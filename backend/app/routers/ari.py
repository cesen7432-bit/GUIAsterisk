import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..database import get_db
from ..models.ari_user import ARIUser
from ..services.ari_client import ari_client
from ..services.config_generator import gen_ari, _write
from ..services.ami_client import ami_client

router = APIRouter()


class ARIUserIn(BaseModel):
    username: str
    password: str
    password_format: str = "plain"
    permissions: str = "read_write"
    stasis_apps: str = ""
    cors_origins: str = "*"


class ARIUserUpdate(BaseModel):
    password: Optional[str] = None
    password_format: Optional[str] = None
    permissions: Optional[str] = None
    stasis_apps: Optional[str] = None
    cors_origins: Optional[str] = None
    is_active: Optional[bool] = None


def _reload(db: Session):
    _write("ari.conf", gen_ari(db))
    asyncio.create_task(ami_client.reload_module("res_ari.so"))


@router.get("/users")
async def list_ari_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    users = db.query(ARIUser).all()
    return [
        {
            "id": u.id, "username": u.username, "permissions": u.permissions,
            "stasis_apps": u.stasis_apps, "cors_origins": u.cors_origins,
            "is_active": u.is_active, "password_format": u.password_format,
        }
        for u in users
    ]


@router.post("/users", status_code=201)
async def create_ari_user(
    body: ARIUserIn, db: Session = Depends(get_db), _=Depends(require_admin)
):
    if db.query(ARIUser).filter(ARIUser.username == body.username).first():
        raise HTTPException(400, "Usuario ARI ya existe")
    u = ARIUser(**body.dict())
    db.add(u)
    db.commit()
    _reload(db)
    return {"id": u.id}


@router.put("/users/{username}")
async def update_ari_user(
    username: str, body: ARIUserUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    u = db.query(ARIUser).filter(ARIUser.username == username).first()
    if not u:
        raise HTTPException(404, "No encontrado")
    for k, v in body.dict(exclude_none=True).items():
        setattr(u, k, v)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.delete("/users/{username}")
async def delete_ari_user(
    username: str, db: Session = Depends(get_db), _=Depends(require_admin)
):
    u = db.query(ARIUser).filter(ARIUser.username == username).first()
    if not u:
        raise HTTPException(404, "No encontrado")
    db.delete(u)
    db.commit()
    _reload(db)
    return {"ok": True}


@router.post("/test")
async def test_ari(_=Depends(get_current_user)):
    try:
        info = await ari_client.get_info()
        return {"ok": True, "info": info}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/apps")
async def list_ari_apps(_=Depends(require_admin)):
    try:
        return await ari_client.get_applications()
    except Exception as e:
        return []


@router.get("/channels")
async def ari_channels(_=Depends(get_current_user)):
    try:
        return await ari_client.get_channels()
    except Exception as e:
        return []
