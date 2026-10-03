"""Ciclo de vida completo de una llamada saliente."""
import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from .ari import ORIGINATE_TIMEOUT, ARIClient
from .db import VoiceCallLog, VoiceContact, get_session
from .local_bridge import run_audio_bridge
from .port_pool import PortPool

logger = logging.getLogger(__name__)

# Timeout de ring local: margen sobre el de Asterisk para recibir su causa de cuelgue
RING_TIMEOUT = ORIGINATE_TIMEOUT + 10
# Duración máxima de conversación
MAX_CALL_SECONDS = 600

# Causas Q.850 que Asterisk reporta en ChannelDestroyed
CAUSE_REJECTED = {17, 21}            # usuario ocupado (rechazo en GSM) / llamada rechazada
CAUSE_NO_ANSWER = {18, 19}           # sin respuesta del usuario / timbró sin contestar
CAUSE_UNAVAILABLE = {20, 27, 31, 34, 38, 41, 42}  # apagado, fuera de servicio, congestión
CAUSE_INVALID = {1, 3, 22, 28}       # número inexistente / mal formado

# Estados de contacto que se reintentan
RETRYABLE = {"no_answer", "rejected"}


@dataclass
class RingResult:
    answered_at: datetime | None = None
    cause: int = 0
    cause_txt: str = ""
    rang: bool = False
    ring_seconds: int = 0
    timed_out: bool = False


async def run_call_session(
    contact_id: int,
    phone: str,
    variables: dict,
    trunk: str,
    max_retries: int,
    retry_delay_minutes: int,
    system_prompt: str,
    first_message: str,
    voice: str,
    vad_threshold: float,
    ari: ARIClient,
    port_pool: PortPool,
):
    log_id = None
    channel_id = None
    bridge_id = None
    ext_channel_id = None
    rtp_port = None

    started_at = datetime.utcnow()

    try:
        # Crear registro de log
        with get_session() as db:
            log = VoiceCallLog(contact_id=contact_id, started_at=started_at)
            db.add(log)
            db.commit()
            db.refresh(log)
            log_id = log.id

        # Originar llamada
        channel_id = await ari.originate(phone, trunk)
        logger.info(f"[{contact_id}] Originando → {phone} channel={channel_id}")

        with get_session() as db:
            db.query(VoiceCallLog).filter_by(id=log_id).update({"channel_id": channel_id})
            db.commit()

        # Suscribir a eventos de este canal
        event_q = ari.event_router.subscribe(channel_id)

        try:
            ring = await _wait_for_answer(event_q)
        finally:
            ari.event_router.unsubscribe(channel_id)

        answered_at = ring.answered_at
        if answered_at is None:
            disposition, contact_status = _classify_unanswered(ring)
            logger.info(
                f"[{contact_id}] No contestada ({disposition}) → {phone} "
                f"causa={ring.cause} {ring.cause_txt!r} timbró={ring.ring_seconds}s"
            )
            _update_contact(contact_id, contact_status, max_retries, retry_delay_minutes)
            _update_log(
                log_id, ended_at=datetime.utcnow(), disposition=disposition,
                summary={
                    "hangup_cause": ring.cause,
                    "hangup_cause_txt": ring.cause_txt,
                    "ring_seconds": ring.ring_seconds,
                },
            )
            return

        logger.info(f"[{contact_id}] Contestó {phone} a las {answered_at}")
        _update_log(log_id, answered_at=answered_at)

        # Puerto RTP y canal externalMedia
        rtp_port = await port_pool.acquire()
        ext_ch = await ari.create_external_media(rtp_port)
        ext_channel_id = ext_ch["id"]
        bridge_id = await ari.create_bridge()
        await ari.add_to_bridge(bridge_id, channel_id, ext_channel_id)

        # Suscribir de nuevo para detectar cuelgue durante la conversación
        hangup_q = ari.event_router.subscribe(channel_id)
        hangup_event = asyncio.Event()

        async def _watch_hangup():
            while True:
                try:
                    event = await asyncio.wait_for(hangup_q.get(), timeout=2)
                    if event.get("type") in ("ChannelDestroyed", "ChannelHangupRequest"):
                        hangup_event.set()
                        return
                except asyncio.TimeoutError:
                    if hangup_event.is_set():
                        return

        watcher = asyncio.create_task(_watch_hangup())

        try:
            transcript, summary = await asyncio.wait_for(
                run_audio_bridge(
                    local_port=rtp_port,
                    system_prompt=system_prompt,
                    first_message=first_message,
                    voice=voice,
                    vad_threshold=vad_threshold,
                    hangup_event=hangup_event,
                ),
                timeout=MAX_CALL_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[{contact_id}] Llamada excedió {MAX_CALL_SECONDS}s — colgando")
            transcript, summary = "", {"resultado": "completado", "resumen": "Duración máxima alcanzada"}
        finally:
            watcher.cancel()
            ari.event_router.unsubscribe(channel_id)

        ended_at = datetime.utcnow()
        duration = int((ended_at - answered_at).total_seconds())
        outcome = summary.get("resultado", "completado")

        with get_session() as db:
            db.query(VoiceCallLog).filter_by(id=log_id).update({
                "ended_at": ended_at,
                "duration_seconds": duration,
                "transcript": transcript,
                "summary": summary,
                "disposition": outcome,
            })
            db.query(VoiceContact).filter_by(id=contact_id).update({
                "status": "voicemail" if outcome == "voicemail" else "completed",
                "result": summary,
                "updated_at": ended_at,
            })
            db.commit()

        logger.info(f"[{contact_id}] Finalizado: {outcome} ({duration}s)")

    except Exception as e:
        logger.exception(f"[{contact_id}] Error en llamada: {e}")
        with get_session() as db:
            db.query(VoiceContact).filter_by(id=contact_id).update({
                "status": "failed",
                "updated_at": datetime.utcnow(),
            })
            if log_id:
                db.query(VoiceCallLog).filter_by(id=log_id).update({
                    "ended_at": datetime.utcnow(),
                    "disposition": "error",
                })
            db.commit()

    finally:
        if channel_id:
            with contextlib.suppress(Exception):
                await ari.hangup(channel_id)
        if bridge_id:
            with contextlib.suppress(Exception):
                await ari.destroy_bridge(bridge_id)
        if rtp_port is not None:
            await port_pool.release(rtp_port)


async def _wait_for_answer(event_q: asyncio.Queue) -> RingResult:
    """Espera ChannelStateChange:Up. Si no contesta, devuelve la causa de cuelgue y cuánto timbró."""
    res = RingResult()
    ring_start = None
    try:
        async with asyncio.timeout(RING_TIMEOUT):
            while True:
                event = await event_q.get()
                etype = event.get("type", "")
                if etype == "ChannelStateChange":
                    state = event.get("channel", {}).get("state", "")
                    if state == "Up":
                        res.answered_at = datetime.utcnow()
                        break
                    if state == "Ringing" and ring_start is None:
                        ring_start = datetime.utcnow()
                        res.rang = True
                elif etype == "ChannelHangupRequest":
                    # Guardar la causa, pero esperar ChannelDestroyed que trae la definitiva
                    if event.get("cause"):
                        res.cause = event["cause"]
                elif etype == "ChannelDestroyed":
                    res.cause = event.get("cause") or res.cause
                    res.cause_txt = event.get("cause_txt", "")
                    break
    except (asyncio.TimeoutError, TimeoutError):
        res.timed_out = True
    if ring_start:
        res.ring_seconds = int((datetime.utcnow() - ring_start).total_seconds())
    return res


def _classify_unanswered(ring: RingResult) -> tuple[str, str]:
    """Devuelve (disposition del log, status del contacto) para una llamada no contestada."""
    if ring.cause in CAUSE_REJECTED:
        return "rejected", "rejected"
    if ring.cause in CAUSE_NO_ANSWER or ring.timed_out:
        return "no_answer", "no_answer"
    if ring.cause in CAUSE_UNAVAILABLE:
        return "unavailable", "no_answer"
    if ring.cause in CAUSE_INVALID:
        return "invalid_number", "failed"
    # Causa genérica (16 normal / 0): decidir por cuánto timbró
    if ring.rang and ring.ring_seconds < ORIGINATE_TIMEOUT - 3:
        return "rejected", "rejected"
    if ring.rang:
        return "no_answer", "no_answer"
    return "unavailable", "no_answer"


def _update_contact(contact_id: int, status: str, max_retries: int, retry_delay: int):
    with get_session() as db:
        c = db.query(VoiceContact).get(contact_id)
        if not c:
            return
        if status in RETRYABLE and c.attempts < max_retries:
            c.status = "pending"
            c.next_attempt_at = datetime.utcnow() + timedelta(minutes=retry_delay)
        else:
            c.status = status
        c.updated_at = datetime.utcnow()
        db.commit()


def _update_log(log_id: int, **kwargs):
    with get_session() as db:
        db.query(VoiceCallLog).filter_by(id=log_id).update(kwargs)
        db.commit()
