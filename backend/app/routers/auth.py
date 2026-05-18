from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from ..database import get_db
from ..models.user import GUIUser

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(GUIUser).filter(GUIUser.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    return {
        "access_token": create_access_token({"sub": str(user.id), "role": user.role}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
    }


@router.get("/me")
async def me(current_user: GUIUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "extension": current_user.extension,
    }


class SetupAdminRequest(BaseModel):
    username: str
    password: str
    full_name: str = "Administrador"


@router.post("/setup-admin")
async def setup_admin(body: SetupAdminRequest, db: Session = Depends(get_db)):
    if db.query(GUIUser).count() > 0:
        raise HTTPException(status_code=400, detail="Ya existen usuarios")
    admin = GUIUser(
        name=body.full_name,
        email=body.username,
        password_hash=get_password_hash(body.password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    return {"message": f"Admin creado: {body.username}"}
