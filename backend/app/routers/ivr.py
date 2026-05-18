from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.ivr import IVR, IVROption
from ..services import ami_reload
from ..services.config_generator import gen_extensions, _write

router = APIRouter()


class IVROptionIn(BaseModel):
    key: str
    destination_type: str
    destination_id: str = ""


class IVRIn(BaseModel):
    name: str
    welcome_audio: str = ""
    timeout: int = 10
    max_attempts: int = 3
    invalid_action: str = "repeat"
    timeout_action: str = "repeat"
    schedule_id: Optional[int] = None
    options: List[IVROptionIn] = []


def _reload(db: Session):
    _write("extensions.conf", gen_extensions(db))
    ami_reload.reload_dialplan()


@router.get("/")
async def list_ivr(db: Session = Depends(get_db), _=Depends(get_current_user)):
    ivrs = db.query(IVR).all()
    return [
        {
            "id": i.id, "name": i.name, "welcome_audio": i.welcome_audio,
            "timeout": i.timeout, "max_attempts": i.max_attempts,
            "options_count": len(i.options),
        }
        for i in ivrs
    ]


@router.get("/{ivr_id}")
async def get_ivr(ivr_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ivr = db.query(IVR).filter(IVR.id == ivr_id).first()
    if not ivr:
        raise HTTPException(404, "No encontrado")
    return {
        "id": ivr.id, "name": ivr.name, "welcome_audio": ivr.welcome_audio,
        "timeout": ivr.timeout, "max_attempts": ivr.max_attempts,
        "invalid_action": ivr.invalid_action, "timeout_action": ivr.timeout_action,
        "options": [{"key": o.key, "destination_type": o.destination_type, "destination_id": o.destination_id} for o in ivr.options],
    }


@router.post("/", status_code=201)
async def create_ivr(
    body: IVRIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    ivr = IVR(**{k: v for k, v in body.dict().items() if k != "options"})
    db.add(ivr)
    db.flush()
    for opt in body.options:
        db.add(IVROption(ivr_id=ivr.id, **opt.dict()))
    db.commit()
    _reload(db)
    return {"id": ivr.id}


@router.put("/{ivr_id}")
async def update_ivr(
    ivr_id: int, body: IVRIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    ivr = db.query(IVR).filter(IVR.id == ivr_id).first()
    if not ivr:
        raise HTTPException(404, "No encontrado")
    for k, v in body.dict(exclude={"options"}).items():
        setattr(ivr, k, v)
    for opt in ivr.options:
        db.delete(opt)
    db.flush()
    for opt in body.options:
        db.add(IVROption(ivr_id=ivr.id, **opt.dict()))
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/{ivr_id}")
async def delete_ivr(
    ivr_id: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    ivr = db.query(IVR).filter(IVR.id == ivr_id).first()
    if not ivr:
        raise HTTPException(404, "No encontrado")
    db.delete(ivr)
    db.commit()
    _reload(db)
    return {"ok": True}
