import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.voicemail import Voicemail
from ..services.ami_client import ami_client
from ..services.config_generator import gen_voicemail, _write

router = APIRouter()


class VoicemailIn(BaseModel):
    extension: str
    password: str = "1234"
    email: str = ""
    attach_audio: bool = True
    delete_after_email: bool = False


def _reload(db: Session):
    _write("voicemail.conf", gen_voicemail(db))
    asyncio.create_task(ami_client.reload_module("app_voicemail.so"))


@router.get("/")
async def list_voicemail(db: Session = Depends(get_db), _=Depends(get_current_user)):
    vms = db.query(Voicemail).all()
    return [
        {
            "id": v.id, "extension": v.extension, "password": v.password,
            "email": v.email, "attach_audio": v.attach_audio,
            "delete_after_email": v.delete_after_email,
        }
        for v in vms
    ]


@router.post("/", status_code=201)
async def create_voicemail(
    body: VoicemailIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(Voicemail).filter(Voicemail.extension == body.extension).first():
        raise HTTPException(400, "Extensión ya tiene buzón")
    vm = Voicemail(**body.dict())
    db.add(vm)
    db.commit()
    _reload(db)
    return {"id": vm.id}


@router.put("/{vm_id}")
async def update_voicemail(
    vm_id: int, body: VoicemailIn,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    vm = db.query(Voicemail).filter(Voicemail.id == vm_id).first()
    if not vm:
        raise HTTPException(404, "No encontrado")
    for k, v in body.dict().items():
        setattr(vm, k, v)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/{vm_id}")
async def delete_voicemail(
    vm_id: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    vm = db.query(Voicemail).filter(Voicemail.id == vm_id).first()
    if not vm:
        raise HTTPException(404, "No encontrado")
    db.delete(vm)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.get("/{extension}/messages")
async def get_messages(extension: str, _=Depends(get_current_user)):
    resp = await ami_client.send_action({"Action": "VoicemailUsersList"})
    return resp or {"messages": []}
