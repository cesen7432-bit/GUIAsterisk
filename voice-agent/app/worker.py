"""Marcador de campaña: lee contactos pendientes y origina llamadas."""
import asyncio
import logging
from datetime import datetime

from .ari import ARIClient
from .call_session import run_call_session
from .db import VoiceCampaign, VoiceContact, VoiceTemplate, get_session
from .port_pool import PortPool
from .templates import render

logger = logging.getLogger(__name__)

# contact_id → asyncio.Task
_active: dict[int, asyncio.Task] = {}


async def run_worker(ari: ARIClient, port_pool: PortPool):
    logger.info("Worker de campañas iniciado")
    while True:
        try:
            await _tick(ari, port_pool)
        except Exception as e:
            logger.error(f"Error en worker: {e}")
        await asyncio.sleep(3)


async def _tick(ari: ARIClient, port_pool: PortPool):
    # Limpiar tareas terminadas
    finished = [cid for cid, t in _active.items() if t.done()]
    for cid in finished:
        _active.pop(cid, None)

    with get_session() as db:
        campaigns = db.query(VoiceCampaign).filter_by(status="active").all()
        if not campaigns:
            return

        now_time = datetime.now().time()

        for campaign in campaigns:
            # Verificar horario
            if not (campaign.schedule_start <= now_time <= campaign.schedule_end):
                continue

            # Cuántos activos tiene esta campaña
            active_ids = set(_active.keys())
            active_for_campaign = (
                db.query(VoiceContact)
                .filter(
                    VoiceContact.campaign_id == campaign.id,
                    VoiceContact.id.in_(active_ids),
                )
                .count()
                if active_ids
                else 0
            )
            slots = campaign.max_concurrent - active_for_campaign
            if slots <= 0:
                continue

            # Buscar contactos pendientes (SELECT … FOR UPDATE SKIP LOCKED)
            contacts = (
                db.query(VoiceContact)
                .filter(
                    VoiceContact.campaign_id == campaign.id,
                    VoiceContact.status == "pending",
                    (VoiceContact.next_attempt_at.is_(None))
                    | (VoiceContact.next_attempt_at <= datetime.utcnow()),
                )
                .with_for_update(skip_locked=True)
                .limit(slots)
                .all()
            )
            if not contacts:
                continue

            template = db.query(VoiceTemplate).get(campaign.template_id)
            if not template:
                logger.warning(f"Campaña {campaign.id}: plantilla {campaign.template_id} no existe")
                continue

            # Reservar como 'calling'
            for c in contacts:
                c.status = "calling"
                c.attempts += 1
            db.commit()

            # Capturar datos antes de cerrar sesión
            trunk = campaign.trunk
            max_retries = campaign.max_retries
            retry_delay = campaign.retry_delay_minutes
            sys_prompt_tpl = template.system_prompt
            first_msg_tpl = template.first_message
            voice = template.voice
            vad = template.vad_threshold

            items = [(c.id, c.phone, dict(c.variables or {})) for c in contacts]

        # Lanzar tareas fuera del contexto de la sesión
        for contact_id, phone, variables in items:
            try:
                system_prompt = render(sys_prompt_tpl, variables)
                first_message = render(first_msg_tpl, variables)
            except ValueError as e:
                logger.error(f"[{contact_id}] Error en plantilla: {e}")
                with get_session() as db:
                    db.query(VoiceContact).filter_by(id=contact_id).update({"status": "failed"})
                    db.commit()
                continue

            task = asyncio.create_task(
                run_call_session(
                    contact_id=contact_id,
                    phone=phone,
                    variables=variables,
                    trunk=trunk,
                    max_retries=max_retries,
                    retry_delay_minutes=retry_delay,
                    system_prompt=system_prompt,
                    first_message=first_message,
                    voice=voice,
                    vad_threshold=vad,
                    ari=ari,
                    port_pool=port_pool,
                )
            )
            _active[contact_id] = task
            logger.info(f"Tarea lanzada para contacto {contact_id} → {phone}")
