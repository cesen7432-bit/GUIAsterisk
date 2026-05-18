import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.route import InboundRoute, OutboundRoute
from ..services.ami_client import ami_client
from ..services.config_generator import gen_extensions, _write

router = APIRouter()


def _reload(db: Session):
    _write("extensions.conf", gen_extensions(db))
    asyncio.create_task(ami_client.reload_module("pbx_config.so"))


class InboundIn(BaseModel):
    did: str = ""
    callerid: str = ""
    destination_type: str
    destination_id: str = ""
    schedule_id: Optional[int] = None


class OutboundIn(BaseModel):
    name: str
    pattern: str
    trunk_id: int
    prefix_add: str = ""
    prefix_remove: int = 0
    recording: bool = False
    schedule_id: Optional[int] = None
    priority: int = 1


@router.get("/inbound")
async def list_inbound(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [
        {
            "id": r.id, "did": r.did, "callerid": r.callerid,
            "destination_type": r.destination_type, "destination_id": r.destination_id,
        }
        for r in db.query(InboundRoute).all()
    ]


@router.post("/inbound", status_code=201)
async def create_inbound(
    body: InboundIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = InboundRoute(**body.dict())
    db.add(r)
    db.commit()
    _reload(db)
    return {"id": r.id}


@router.put("/inbound/{rid}")
async def update_inbound(
    rid: int, body: InboundIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = db.query(InboundRoute).filter(InboundRoute.id == rid).first()
    if not r:
        raise HTTPException(404, "No encontrada")
    for k, v in body.dict().items():
        setattr(r, k, v)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/inbound/{rid}")
async def delete_inbound(
    rid: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = db.query(InboundRoute).filter(InboundRoute.id == rid).first()
    if not r:
        raise HTTPException(404, "No encontrada")
    db.delete(r)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.get("/outbound")
async def list_outbound(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [
        {
            "id": r.id, "name": r.name, "pattern": r.pattern,
            "trunk_id": r.trunk_id, "prefix_add": r.prefix_add,
            "prefix_remove": r.prefix_remove, "priority": r.priority,
            "recording": r.recording,
        }
        for r in db.query(OutboundRoute).filter(OutboundRoute.is_active == True).order_by(OutboundRoute.priority).all()
    ]


@router.post("/outbound", status_code=201)
async def create_outbound(
    body: OutboundIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = OutboundRoute(**body.dict())
    db.add(r)
    db.commit()
    _reload(db)
    return {"id": r.id}


@router.put("/outbound/{rid}")
async def update_outbound(
    rid: int, body: OutboundIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = db.query(OutboundRoute).filter(OutboundRoute.id == rid).first()
    if not r:
        raise HTTPException(404, "No encontrada")
    for k, v in body.dict().items():
        setattr(r, k, v)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/outbound/{rid}")
async def delete_outbound(
    rid: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    r = db.query(OutboundRoute).filter(OutboundRoute.id == rid).first()
    if not r:
        raise HTTPException(404, "No encontrada")
    r.is_active = False
    db.commit()
    _reload(db)
    return {"ok": True}
