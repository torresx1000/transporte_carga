from datetime import datetime, timezone
from math import ceil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.security import hash_password
from app.models.entities import Client, User
from app.schemas.responses import PageResponse, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=PageResponse[UsuarioResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    total = db.scalar(select(func.count()).select_from(User).where(User.deleted_at.is_(None))) or 0
    items = db.scalars(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size),
        "items": [
            {
                "id": item.id,
                "email": item.email,
                "role": item.role,
                "active": item.active,
                "data": item.data,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


@router.post("", status_code=201, response_model=UsuarioResponse)
def create_user(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role = str(payload.get("role", "operador"))
    if not email or len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise HTTPException(400, "Contraseña: mínimo 8 y máximo 72 bytes; correo obligatorio")
    if role not in {"admin", "operador", "chofer", "cliente"}:
        raise HTTPException(400, "Rol no válido")
    client_id = payload.get("client_id")
    if client_id and role != "cliente":
        raise HTTPException(400, "Solo los usuarios cliente pueden vincularse a un cliente")
    linked_client = db.get(Client, client_id) if client_id else None
    if client_id and (linked_client is None or linked_client.deleted_at is not None):
        raise HTTPException(404, "Cliente no encontrado")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "El correo ya está registrado")
    item = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        active=True,
        created_by=user.id,
        data={
            "name": payload.get("name", ""),
            "client_id": client_id if role == "cliente" else None,
        },
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "email": item.email,
        "role": item.role,
        "active": item.active,
        "data": item.data,
    }


@router.patch("/{user_id}", response_model=UsuarioResponse)
def update_user(
    user_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    item = db.get(User, user_id)
    if not item or item.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    if "email" in payload:
        item.email = str(payload["email"]).strip().lower()
    if "role" in payload:
        if payload["role"] not in {"admin", "operador", "chofer", "cliente"}:
            raise HTTPException(400, "Rol no válido")
        item.role = payload["role"]
    target_role = payload.get("role", item.role)
    client_id = payload.get("client_id", item.data.get("client_id"))
    if target_role != "cliente" and "client_id" not in payload:
        client_id = None
    if client_id and target_role != "cliente":
        raise HTTPException(400, "Solo los usuarios cliente pueden vincularse a un cliente")
    linked_client = db.get(Client, client_id) if client_id else None
    if client_id and (linked_client is None or linked_client.deleted_at is not None):
        raise HTTPException(404, "Cliente no encontrado")
    if "active" in payload:
        item.active = bool(payload["active"])
    if "password" in payload:
        if len(str(payload["password"])) < 8 or len(str(payload["password"]).encode("utf-8")) > 72:
            raise HTTPException(400, "La contraseña debe tener entre 8 y 72 bytes")
        item.password_hash = hash_password(str(payload["password"]))
    item.data = {
        **item.data,
        **{key: payload[key] for key in ("name", "client_id") if key in payload},
    }
    if target_role != "cliente":
        item.data.pop("client_id", None)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "email": item.email,
        "role": item.role,
        "active": item.active,
        "data": item.data,
    }


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))
):
    item = db.get(User, user_id)
    if not item or item.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    item.active = False
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None
