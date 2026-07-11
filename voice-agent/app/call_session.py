"""Ciclo de vida completo de una llamada saliente."""
import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from .ari import ARIClient
from .db import VoiceCallLog, VoiceContact, get_session
from .openai_bridge import run_audio_bridge
from .port_pool import PortPool

logger = logging.getLogger(__name__)

# Timeout de ring (segundos antes de rendirse)
RING_TIMEOUT = 35
# Duración máxima de conversación
MAX_CALL_SECONDS = 600


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
            answered_at = await _wait_for_answer(event_q)
        finally:
            ari.event_router.unsubscribe(channel_id)

        if answered_at is None:
            # No contestó
            logger.info(f"[{contact_id}] Sin respuesta → {phone}")
            _update_contact(contact_id, "no_answer", max_retries, retry_delay_minutes)
            _update_log(log_id, ended_at=datetime.utcnow(), disposition="no_answer")
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


async def _wait_for_answer(event_q: asyncio.Queue) -> datetime | None:
    """Espera ChannelStateChange:Up. Devuelve hora de respuesta o None si timeout/cuelgue."""
    try:
        async with asyncio.timeout(RING_TIMEOUT):
            while True:
                event = await event_q.get()
                etype = event.get("type", "")
                if etype == "ChannelStateChange":
                    state = event.get("channel", {}).get("state", "")
                    if state == "Up":
                        return datetime.utcnow()
                elif etype in ("ChannelDestroyed", "ChannelHangupRequest"):
                    return None
    except (asyncio.TimeoutError, TimeoutError):
        return None


def _update_contact(contact_id: int, status: str, max_retries: int, retry_delay: int):
    with get_session() as db:
        c = db.query(VoiceContact).get(contact_id)
        if not c:
            return
        if status == "no_answer" and c.attempts < max_retries:
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
