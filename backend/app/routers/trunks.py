from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.trunk import Trunk
from ..services.ami_client import ami_client
from ..services.config_generator import gen_pjsip, _write

router = APIRouter()


class TrunkIn(BaseModel):
    name: str
    username: str
    password: str
    host: str
    port: int = 5060
    codecs: str = "ulaw,alaw"
    context_in: str = "from-trunk"
    match_ip: bool = False
    registration: str = "send"
    qualify_frequency: int = 60
    direct_media: bool = False


class TrunkUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    codecs: Optional[str] = None
    context_in: Optional[str] = None
    match_ip: Optional[bool] = None
    registration: Optional[str] = None
    qualify_frequency: Optional[int] = None
    direct_media: Optional[bool] = None


def _reload(db: Session):
    import asyncio
    _write("pjsip.conf", gen_pjsip(db))
    asyncio.create_task(ami_client.reload_module("res_pjsip.so"))


@router.get("/")
async def list_trunks(db: Session = Depends(get_db), _=Depends(get_current_user)):
    trunks = db.query(Trunk).filter(Trunk.is_active == True).all()
    return [
        {
            "id": t.id, "name": t.name, "username": t.username,
            "host": t.host, "port": t.port, "codecs": t.codecs,
            "registration": t.registration, "qualify_frequency": t.qualify_frequency,
            "direct_media": t.direct_media, "match_ip": t.match_ip,
        }
        for t in trunks
    ]


@router.post("/", status_code=201)
async def create_trunk(
    body: TrunkIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(Trunk).filter(Trunk.name == body.name).first():
        raise HTTPException(status_code=400, detail="Nombre ya existe")
    trunk = Trunk(**body.dict())
    db.add(trunk)
    db.commit()
    db.refresh(trunk)
    _reload(db)
    return {"id": trunk.id}


@router.put("/{trunk_id}")
async def update_trunk(
    trunk_id: int, body: TrunkUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    trunk = db.query(Trunk).filter(Trunk.id == trunk_id).first()
    if not trunk:
        raise HTTPException(status_code=404, detail="No encontrado")
    for k, v in body.dict(exclude_none=True).items():
        setattr(trunk, k, v)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/{trunk_id}")
async def delete_trunk(
    trunk_id: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    trunk = db.query(Trunk).filter(Trunk.id == trunk_id).first()
    if not trunk:
        raise HTTPException(status_code=404, detail="No encontrado")
    trunk.is_active = False
    db.commit()
    _reload(db)
    return {"ok": True}


@router.post("/{trunk_id}/register")
async def force_register(trunk_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    trunk = db.query(Trunk).filter(Trunk.id == trunk_id).first()
    if not trunk:
        raise HTTPException(status_code=404, detail="No encontrado")
    resp = await ami_client.send_action({"Action": "PJSIPRegister", "Registration": f"{trunk.name}-reg"})
    return resp or {"ok": True}
