from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.followme import FollowMe, FollowMeDestination
from ..services import ami_reload
from ..services.config_generator import gen_followme, _write

router = APIRouter()


class DestIn(BaseModel):
    number: str
    timeout: int = 20
    order: int = 1


class FollowMeIn(BaseModel):
    extension: str
    is_active: bool = False
    initial_ring_time: int = 20
    strategy: str = "sequential"
    music_on_hold: str = "default"
    confirm_calls: bool = False
    destinations: List[DestIn] = []


def _reload(db: Session):
    _write("followme.conf", gen_followme(db))
    ami_reload.reload_followme()


@router.get("/")
async def list_followme(db: Session = Depends(get_db), _=Depends(get_current_user)):
    fms = db.query(FollowMe).all()
    return [
        {
            "id": fm.id, "extension": fm.extension, "is_active": fm.is_active,
            "strategy": fm.strategy, "destinations_count": len(fm.destinations),
        }
        for fm in fms
    ]


@router.get("/{extension}")
async def get_followme(extension: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    fm = db.query(FollowMe).filter(FollowMe.extension == extension).first()
    if not fm:
        raise HTTPException(404, "No encontrado")
    return {
        "id": fm.id, "extension": fm.extension, "is_active": fm.is_active,
        "initial_ring_time": fm.initial_ring_time, "strategy": fm.strategy,
        "music_on_hold": fm.music_on_hold, "confirm_calls": fm.confirm_calls,
        "destinations": [{"number": d.number, "timeout": d.timeout, "order": d.order} for d in fm.destinations],
    }


@router.post("/", status_code=201)
async def create_followme(
    body: FollowMeIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(FollowMe).filter(FollowMe.extension == body.extension).first():
        raise HTTPException(400, "Ya existe Follow Me para esta extensión")
    fm = FollowMe(**{k: v for k, v in body.dict().items() if k != "destinations"})
    db.add(fm)
    db.flush()
    for d in body.destinations:
        db.add(FollowMeDestination(followme_id=fm.id, **d.dict()))
    db.commit()
    _reload(db)
    return {"id": fm.id}


@router.put("/{fm_id}")
async def update_followme(
    fm_id: int, body: FollowMeIn,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    fm = db.query(FollowMe).filter(FollowMe.id == fm_id).first()
    if not fm:
        raise HTTPException(404, "No encontrado")
    for k, v in body.dict(exclude={"destinations"}).items():
        setattr(fm, k, v)
    for d in fm.destinations:
        db.delete(d)
    db.flush()
    for d in body.destinations:
        db.add(FollowMeDestination(followme_id=fm.id, **d.dict()))
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/{fm_id}")
async def delete_followme(
    fm_id: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    fm = db.query(FollowMe).filter(FollowMe.id == fm_id).first()
    if not fm:
        raise HTTPException(404, "No encontrado")
    db.delete(fm)
    db.commit()
    _reload(db)
    return {"ok": True}
