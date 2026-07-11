import csv
import io
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.campaign import VoiceCampaign, VoiceCallLog, VoiceContact, VoiceTemplate

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class TemplateIn(BaseModel):
    name: str
    system_prompt: str
    first_message: str
    voice: str = "alloy"
    vad_threshold: float = 0.6


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    first_message: Optional[str] = None
    voice: Optional[str] = None
    vad_threshold: Optional[float] = None


class CampaignIn(BaseModel):
    name: str
    template_id: int
    max_concurrent: int = 4
    schedule_start: str = "09:00"
    schedule_end: str = "18:00"
    max_retries: int = 3
    retry_delay_minutes: int = 120
    trunk: str = "openvox"


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    template_id: Optional[int] = None
    status: Optional[str] = None
    max_concurrent: Optional[int] = None
    schedule_start: Optional[str] = None
    schedule_end: Optional[str] = None
    max_retries: Optional[int] = None
    retry_delay_minutes: Optional[int] = None
    trunk: Optional[str] = None


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates/")
def list_templates(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(VoiceTemplate).order_by(VoiceTemplate.id.desc()).all()


@router.post("/templates/", status_code=201)
def create_template(body: TemplateIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = VoiceTemplate(**body.dict())
    db.add(t); db.commit(); db.refresh(t)
    return t


@router.get("/templates/{tid}")
def get_template(tid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(VoiceTemplate).get(tid)
    if not t:
        raise HTTPException(404, "No encontrado")
    return t


@router.put("/templates/{tid}")
def update_template(
    tid: int, body: TemplateUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    t = db.query(VoiceTemplate).get(tid)
    if not t:
        raise HTTPException(404)
    for k, v in body.dict(exclude_none=True).items():
        setattr(t, k, v)
    db.commit()
    return t


@router.delete("/templates/{tid}")
def delete_template(tid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = db.query(VoiceTemplate).get(tid)
    if not t:
        raise HTTPException(404)
    db.delete(t); db.commit()
    return {"ok": True}


# ── Campaigns ─────────────────────────────────────────────────────────────────

def _campaign_dict(c: VoiceCampaign, db: Session) -> dict:
    total = db.query(VoiceContact).filter_by(campaign_id=c.id).count()
    pending = db.query(VoiceContact).filter_by(campaign_id=c.id, status="pending").count()
    calling = db.query(VoiceContact).filter_by(campaign_id=c.id, status="calling").count()
    completed = db.query(VoiceContact).filter_by(campaign_id=c.id, status="completed").count()
    return {
        "id": c.id, "name": c.name, "status": c.status,
        "template_id": c.template_id, "max_concurrent": c.max_concurrent,
        "schedule_start": str(c.schedule_start), "schedule_end": str(c.schedule_end),
        "max_retries": c.max_retries, "retry_delay_minutes": c.retry_delay_minutes,
        "trunk": c.trunk, "created_at": c.created_at,
        "stats": {"total": total, "pending": pending, "calling": calling, "completed": completed},
    }


@router.get("/")
def list_campaigns(db: Session = Depends(get_db), _=Depends(get_current_user)):
    campaigns = db.query(VoiceCampaign).order_by(VoiceCampaign.id.desc()).all()
    return [_campaign_dict(c, db) for c in campaigns]


@router.post("/", status_code=201)
def create_campaign(body: CampaignIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    data = body.dict()
    c = VoiceCampaign(**data)
    db.add(c); db.commit(); db.refresh(c)
    return _campaign_dict(c, db)


@router.get("/{cid}")
def get_campaign(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(VoiceCampaign).get(cid)
    if not c:
        raise HTTPException(404)
    return _campaign_dict(c, db)


@router.put("/{cid}")
def update_campaign(
    cid: int, body: CampaignUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    c = db.query(VoiceCampaign).get(cid)
    if not c:
        raise HTTPException(404)
    for k, v in body.dict(exclude_none=True).items():
        setattr(c, k, v)
    db.commit()
    return _campaign_dict(c, db)


@router.delete("/{cid}")
def delete_campaign(cid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(VoiceCampaign).get(cid)
    if not c:
        raise HTTPException(404)
    db.delete(c); db.commit()
    return {"ok": True}


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.post("/{cid}/contacts/upload")
async def upload_contacts(
    cid: int, file: UploadFile = File(...),
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    """CSV con encabezados. Columna 'phone' obligatoria. El resto son variables de plantilla."""
    if not db.query(VoiceCampaign).get(cid):
        raise HTTPException(404, "Campaña no encontrada")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "phone" not in reader.fieldnames:
        raise HTTPException(400, "CSV debe tener columna 'phone'")

    added = 0
    for row in reader:
        phone = row.pop("phone", "").strip()
        if not phone:
            continue
        db.add(VoiceContact(campaign_id=cid, phone=phone, variables=dict(row)))
        added += 1
    db.commit()
    return {"added": added}


@router.get("/{cid}/contacts")
def list_contacts(
    cid: int, status: Optional[str] = None,
    offset: int = 0, limit: int = 100,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(VoiceContact).filter_by(campaign_id=cid)
    if status:
        q = q.filter_by(status=status)
    total = q.count()
    items = q.order_by(VoiceContact.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": items}


@router.delete("/{cid}/contacts")
def reset_contacts(cid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    """Reinicia todos los contactos a 'pending' para re-marcar."""
    db.query(VoiceContact).filter_by(campaign_id=cid).update({
        "status": "pending", "attempts": 0, "next_attempt_at": None, "result": None,
    })
    db.commit()
    return {"ok": True}


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/{cid}/logs")
def list_logs(
    cid: int, limit: int = 50,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    contact_ids = [
        r[0] for r in db.query(VoiceContact.id).filter_by(campaign_id=cid).all()
    ]
    if not contact_ids:
        return []
    return (
        db.query(VoiceCallLog)
        .filter(VoiceCallLog.contact_id.in_(contact_ids))
        .order_by(VoiceCallLog.id.desc())
        .limit(limit)
        .all()
    )
