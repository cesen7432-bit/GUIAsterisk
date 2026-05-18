from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin, require_supervisor
from ..database import get_db
from ..models.queue import Queue, QueueMember
from ..services import ami_reload
from ..services.ari_client import ari_client
from ..services.config_generator import gen_queues, _write

router = APIRouter()


class MemberIn(BaseModel):
    extension: str
    penalty: int = 0


class QueueIn(BaseModel):
    name: str
    strategy: str = "ringall"
    agent_timeout: int = 30
    retry: int = 5
    wrapup_time: int = 5
    max_callers: int = 0
    music_on_hold: str = "default"
    announce_position: bool = False
    announce_hold_time: bool = False
    announce_frequency: int = 30
    recording: bool = False
    members: List[MemberIn] = []


def _reload(db: Session):
    _write("queues.conf", gen_queues(db))
    ami_reload.reload_queues()


@router.get("/")
async def list_queues(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return [
        {
            "id": q.id, "name": q.name, "strategy": q.strategy,
            "agent_timeout": q.agent_timeout, "recording": q.recording,
            "members_count": len(q.members),
        }
        for q in db.query(Queue).all()
    ]


@router.get("/{queue_id}")
async def get_queue(queue_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Queue).filter(Queue.id == queue_id).first()
    if not q:
        raise HTTPException(404, "No encontrada")
    return {
        "id": q.id, "name": q.name, "strategy": q.strategy,
        "agent_timeout": q.agent_timeout, "retry": q.retry,
        "wrapup_time": q.wrapup_time, "max_callers": q.max_callers,
        "music_on_hold": q.music_on_hold, "announce_position": q.announce_position,
        "announce_hold_time": q.announce_hold_time, "announce_frequency": q.announce_frequency,
        "recording": q.recording,
        "members": [{"extension": m.extension, "penalty": m.penalty} for m in q.members],
    }


@router.post("/", status_code=201)
async def create_queue(
    body: QueueIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(Queue).filter(Queue.name == body.name).first():
        raise HTTPException(400, "Nombre ya existe")
    q = Queue(**{k: v for k, v in body.dict().items() if k != "members"})
    db.add(q)
    db.flush()
    for m in body.members:
        db.add(QueueMember(queue_id=q.id, **m.dict()))
    db.commit()
    _reload(db)
    return {"id": q.id}


@router.put("/{queue_id}")
async def update_queue(
    queue_id: int, body: QueueIn,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    q = db.query(Queue).filter(Queue.id == queue_id).first()
    if not q:
        raise HTTPException(404, "No encontrada")
    for k, v in body.dict(exclude={"members"}).items():
        setattr(q, k, v)
    for m in q.members:
        db.delete(m)
    db.flush()
    for m in body.members:
        db.add(QueueMember(queue_id=q.id, **m.dict()))
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/{queue_id}")
async def delete_queue(
    queue_id: int, db: Session = Depends(get_db), _=Depends(require_admin)
):
    q = db.query(Queue).filter(Queue.id == queue_id).first()
    if not q:
        raise HTTPException(404, "No encontrada")
    db.delete(q)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.get("/{queue_name}/realtime")
async def queue_realtime(queue_name: str, _=Depends(require_supervisor)):
    try:
        channels = await ari_client.get_channels()
        return {"channels": channels, "queue": queue_name}
    except Exception as e:
        return {"error": str(e)}


@router.post("/{queue_name}/pause")
async def pause_agent(
    queue_name: str, extension: str, paused: bool = True, reason: str = "",
    _=Depends(require_supervisor)
):
    ami_reload._send(f"queue {'pause' if paused else 'unpause'} member PJSIP/{extension} queue {queue_name} reason {reason}")
    return {"ok": True}
