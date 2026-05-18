from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_password_hash, require_admin
from ..database import get_db
from ..models.user import GUIUser, UserPermission

router = APIRouter()


class UserIn(BaseModel):
    name: str
    email: str
    password: str
    role: str = "agent"
    extension: str = ""
    is_active: bool = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    extension: Optional[str] = None
    is_active: Optional[bool] = None


class PermIn(BaseModel):
    module: str
    can_view: bool = True
    can_edit: bool = False
    can_delete: bool = False


@router.get("/")
async def list_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    users = db.query(GUIUser).all()
    return [
        {
            "id": u.id, "name": u.name, "email": u.email,
            "role": u.role, "extension": u.extension, "is_active": u.is_active,
        }
        for u in users
    ]


@router.post("/", status_code=201)
async def create_user(body: UserIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(GUIUser).filter(GUIUser.email == body.email).first():
        raise HTTPException(400, "Email ya existe")
    user = GUIUser(
        name=body.name, email=body.email,
        password_hash=get_password_hash(body.password),
        role=body.role, extension=body.extension, is_active=body.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id}


@router.put("/{user_id}")
async def update_user(
    user_id: int, body: UserUpdate,
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    user = db.query(GUIUser).filter(GUIUser.id == user_id).first()
    if not user:
        raise HTTPException(404, "No encontrado")
    if body.name:
        user.name = body.name
    if body.password:
        user.password_hash = get_password_hash(body.password)
    if body.role:
        user.role = body.role
    if body.extension is not None:
        user.extension = body.extension
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(GUIUser).filter(GUIUser.id == user_id).first()
    if not user:
        raise HTTPException(404, "No encontrado")
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.put("/{user_id}/permissions")
async def set_permissions(
    user_id: int, perms: List[PermIn],
    db: Session = Depends(get_db), _=Depends(require_admin)
):
    user = db.query(GUIUser).filter(GUIUser.id == user_id).first()
    if not user:
        raise HTTPException(404, "No encontrado")
    for p in user.permissions:
        db.delete(p)
    db.flush()
    for p in perms:
        db.add(UserPermission(user_id=user_id, **p.dict()))
    db.commit()
    return {"ok": True}
