from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.extension import Extension
from ..services import ami_reload
from ..services.config_generator import gen_pjsip, gen_extensions, _write

router = APIRouter()


class ExtensionIn(BaseModel):
    number: str
    name: str
    callerid: Optional[str] = None
    password: str
    type: str = "sip"
    context: str = "from-internal"
    codecs: str = "ulaw,alaw"
    voicemail_enabled: bool = False
    recording: str = "never"
    followme_enabled: bool = False
    blacklist_enabled: bool = False
    language: str = "es"


class ExtensionUpdate(BaseModel):
    name: Optional[str] = None
    callerid: Optional[str] = None
    password: Optional[str] = None
    type: Optional[str] = None
    codecs: Optional[str] = None
    voicemail_enabled: Optional[bool] = None
    recording: Optional[str] = None
    followme_enabled: Optional[bool] = None
    blacklist_enabled: Optional[bool] = None
    language: Optional[str] = None


def _reload(db: Session):
    _write("pjsip.conf", gen_pjsip(db))
    _write("extensions.conf", gen_extensions(db))
    ami_reload.reload_pjsip()
    ami_reload.reload_dialplan()


@router.get("/")
async def list_extensions(db: Session = Depends(get_db), _=Depends(get_current_user)):
    exts = db.query(Extension).filter(Extension.is_active == True).all()
    result = []
    for e in exts:
        result.append({
            "id": e.id, "number": e.number, "name": e.name,
            "callerid": e.callerid, "type": e.type, "context": e.context,
            "codecs": e.codecs, "voicemail_enabled": e.voicemail_enabled,
            "recording": e.recording, "followme_enabled": e.followme_enabled,
            "blacklist_enabled": e.blacklist_enabled, "language": e.language,
        })
    return result


@router.post("/", status_code=201)
async def create_extension(
    body: ExtensionIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(Extension).filter(Extension.number == body.number).first():
        raise HTTPException(status_code=400, detail="Número ya existe")
    ext = Extension(**body.dict())
    db.add(ext)
    db.commit()
    db.refresh(ext)
    _reload(db)
    return {"id": ext.id, "number": ext.number}


@router.put("/{ext_id}")
async def update_extension(
    ext_id: int, body: ExtensionUpdate, db: Session = Depends(get_db), _=Depends(require_admin)
):
    ext = db.query(Extension).filter(Extension.id == ext_id).first()
    if not ext:
        raise HTTPException(status_code=404, detail="No encontrada")
    for k, v in body.dict(exclude_none=True).items():
        if k != 'password' or v:
            setattr(ext, k, v)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/{ext_id}")
async def delete_extension(
    ext_id: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    ext = db.query(Extension).filter(Extension.id == ext_id).first()
    if not ext:
        raise HTTPException(status_code=404, detail="No encontrada")
    ext.is_active = False
    db.commit()
    _reload(db)
    return {"ok": True}


@router.post("/{ext_id}/spy")
async def spy_extension(
    ext_id: int, mode: str = "q",
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    ext = db.query(Extension).filter(Extension.id == ext_id).first()
    if not ext:
        raise HTTPException(status_code=404, detail="No encontrada")
    ami_reload._send(f"channel spy PJSIP/{ext.number} PJSIP/spy-{ext.number}")
    return {"Response": "Sent"}


@router.post("/{channel_id}/hangup")
async def hangup_channel(channel_id: str, _=Depends(require_admin)):
    ami_reload._send(f"channel request hangup {channel_id}")
    return {"ok": True}
