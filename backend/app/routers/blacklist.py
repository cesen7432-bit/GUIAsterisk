import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.blacklist import Blacklist
from ..services.ami_client import ami_client

router = APIRouter()


class BlacklistIn(BaseModel):
    number: str
    reason: str = ""


@router.get("/")
async def list_blacklist(db: Session = Depends(get_db), _=Depends(get_current_user)):
    items = db.query(Blacklist).order_by(Blacklist.created_at.desc()).all()
    return [
        {"id": b.id, "number": b.number, "reason": b.reason, "created_at": b.created_at}
        for b in items
    ]


@router.post("/", status_code=201)
async def add_to_blacklist(
    body: BlacklistIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(Blacklist).filter(Blacklist.number == body.number).first():
        raise HTTPException(400, "Número ya está en lista negra")
    b = Blacklist(number=body.number, reason=body.reason)
    db.add(b)
    db.commit()
    # Add to Asterisk DB
    await ami_client.send_action({
        "Action": "DBPut", "Family": "blacklist", "Key": body.number, "Val": "1"
    })
    return {"id": b.id}


@router.delete("/{number}")
async def remove_from_blacklist(
    number: str, db: Session = Depends(get_db), _=Depends(require_admin)
):
    b = db.query(Blacklist).filter(Blacklist.number == number).first()
    if not b:
        raise HTTPException(404, "No encontrado")
    db.delete(b)
    db.commit()
    await ami_client.send_action({
        "Action": "DBDel", "Family": "blacklist", "Key": number
    })
    return {"ok": True}
