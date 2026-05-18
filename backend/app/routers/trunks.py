from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.trunk import Trunk
from ..services import ami_reload
from ..services.config_generator import gen_pjsip, _write

router = APIRouter()


class TrunkIn(BaseModel):
    name: str
    username: str
    password: str
    host: str
    nat_ip: Optional[str] = None
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
    nat_ip: Optional[str] = None
    port: Optional[int] = None
    codecs: Optional[str] = None
    context_in: Optional[str] = None
    match_ip: Optional[bool] = None
    registration: Optional[str] = None
    qualify_frequency: Optional[int] = None
    direct_media: Optional[bool] = None


def _reload(db: Session):
    _write("pjsip.conf", gen_pjsip(db))
    ami_reload.reload_pjsip()


@router.get("/")
async def list_trunks(db: Session = Depends(get_db), _=Depends(get_current_user)):
    trunks = db.query(Trunk).filter(Trunk.is_active == True).all()
    return [
        {
            "id": t.id, "name": t.name, "username": t.username,
            "host": t.host, "nat_ip": t.nat_ip, "port": t.port, "codecs": t.codecs,
            "context_in": t.context_in, "registration": t.registration,
            "qualify_frequency": t.qualify_frequency,
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
        if k != 'password' or v:
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
    ami_reload._send(f"pjsip send register {trunk.name}-registration")
    return {"ok": True}
