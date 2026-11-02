from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import create_token_pair, decode_token
from app.core.security import hash_password, verify_password
from app.models.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, tags=["usuarios"])
def register(payload: dict[str, Any], db: Session = Depends(get_db)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    if not email or len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise HTTPException(400, "Correo y contraseña (mínimo 8 caracteres) son obligatorios")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "El correo ya está registrado")
    # Public registration cannot grant privileged roles.
    role = "cliente"
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        data={"name": payload.get("name", "")},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login", tags=["usuarios"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(User.email == form.username.lower(), User.deleted_at.is_(None))
    )
    if not user or not user.active or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            401, "Correo o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"}
        )
    return {
        **create_token_pair(user.id),
        "user": {"id": user.id, "email": user.email, "role": user.role},
    }


@router.post("/refresh", tags=["usuarios"])
def refresh(payload: dict[str, str], db: Session = Depends(get_db)):
    try:
        user_id = decode_token(payload.get("refresh_token", ""), "refresh")["sub"]
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    user = db.get(User, user_id)
    if not user or not user.active or user.deleted_at is not None:
        raise HTTPException(401, "Usuario no autorizado")
    return create_token_pair(user.id)
