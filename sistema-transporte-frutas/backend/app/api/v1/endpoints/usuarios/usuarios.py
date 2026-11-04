from datetime import datetime, timezone
from math import ceil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import has_permission, require_permission, require_roles
from app.core.security import hash_password
from app.models.entities import Client, User
from app.models.roles import AccessRole, AccessRoleAudit
from app.schemas.responses import PageResponse, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

DEFAULT_ROLE_NAMES = {
    "admin": "Administrador",
    "operador": "Operaciones",
    "chofer": "Conductor",
    "cliente": "Cliente",
}


def _role_name(user: User) -> str:
    if user.permission_role:
        return user.permission_role.name
    return DEFAULT_ROLE_NAMES.get(str(user.role), str(user.role))


@router.get("", response_model=PageResponse[UsuarioResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("usuarios.ver")),
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
                "role": item.permission_role.slug if item.permission_role else item.role,
                "role_name": _role_name(item),
                "active": item.active,
                "data": item.data,
                "created_at": item.created_at,
                "permission_role_id": item.permission_role_id,
            }
            for item in items
        ],
    }


@router.post("", status_code=201, response_model=UsuarioResponse)
def create_user(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("usuarios.crear")),
):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    role_slug = str(payload.get("role") or ("operador" if str(user.role) == "admin" else "chofer"))
    is_admin = str(user.role) == "admin"
    if "role" in payload and not is_admin and not has_permission(
        user, "usuarios.asignar_roles", db, request
    ):
        raise HTTPException(403, "No tienes permiso para asignar el rol inicial del usuario")
    if role_slug == "admin" and not is_admin:
        raise HTTPException(403, "El rol administrador no se puede asignar")
    role = role_slug if role_slug in {"admin", "operador", "chofer", "cliente"} else "operador"
    access_role = None
    if role_slug != "admin":
        access_role = db.scalar(
            select(AccessRole).where(
                AccessRole.slug == role_slug,
                AccessRole.deleted_at.is_(None),
            )
        )
        if access_role is None and role_slug not in {"operador", "chofer", "cliente"}:
            raise HTTPException(404, "Rol no encontrado")
        if access_role and access_role.slug == "admin":
            raise HTTPException(403, "El rol administrador no se puede asignar")
        if not is_admin and access_role:
            own_permissions = set(
                user.permission_role.permissions if user.permission_role else []
            )
            unauthorized = set(access_role.permissions or []) - own_permissions
            if unauthorized:
                raise HTTPException(
                    403,
                    "No puedes asignar un rol con permisos que no tienes autorizados: "
                    + ", ".join(sorted(unauthorized)),
                )
    if not email or len(password) < 8 or len(password.encode("utf-8")) > 72:
        raise HTTPException(400, "Contraseña: mínimo 8 y máximo 72 bytes; correo obligatorio")
    if role not in {"admin", "operador", "chofer", "cliente"}:
        raise HTTPException(400, "Rol no válido")
    if role == "cliente" and not payload.get("client_id"):
        raise HTTPException(422, "Selecciona un cliente para esta cuenta")
    active = payload.get("active", True)
    if not isinstance(active, bool):
        raise HTTPException(422, "El estado activo debe ser verdadero o falso")
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
        permission_role_id=access_role.id if access_role else None,
        active=active,
        created_by=user.id,
        data={
            "name": payload.get("name", ""),
            "client_id": client_id if role == "cliente" else None,
        },
    )
    db.add(item)
    db.add(
        AccessRoleAudit(
            role_id=access_role.id if access_role else None,
            actor_email=user.email,
            action="asignar_rol",
            details={
                "user_email": email,
                "role": role_slug,
                "source": "crear_usuario",
            },
            created_by=user.id,
            data={},
        )
    )
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "email": item.email,
        "role": item.permission_role.slug if item.permission_role else item.role,
        "role_name": _role_name(item),
        "active": item.active,
        "data": item.data,
        "permission_role_id": item.permission_role_id,
    }


@router.get("/{user_id}", response_model=UsuarioResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("usuarios.ver")),
):
    item = db.get(User, user_id)
    if not item or item.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    return {
        "id": item.id,
        "email": item.email,
        "role": item.permission_role.slug if item.permission_role else item.role,
        "role_name": _role_name(item),
        "active": item.active,
        "data": item.data,
        "permission_role_id": item.permission_role_id,
    }


@router.patch("/{user_id}", response_model=UsuarioResponse)
def update_user(
    user_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("usuarios.editar")),
):
    item = db.get(User, user_id)
    if not item or item.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    previous_role_id = item.permission_role_id
    previous_client_id = (item.data or {}).get("client_id")
    if "email" in payload:
        item.email = str(payload["email"]).strip().lower()
    if "role" in payload:
        if not has_permission(admin, "usuarios.asignar_roles", db, request):
            raise HTTPException(403, "No tienes permiso para asignar roles")
        if admin.id == item.id:
            raise HTTPException(403, "No puedes cambiar tu propio rol")
    if str(item.role) == "admin" and str(admin.role) != "admin":
        raise HTTPException(403, "No puedes modificar la cuenta de un administrador")
    if "role" in payload:
        role_slug = str(payload["role"]).strip()
        if role_slug == "admin":
            raise HTTPException(403, "El rol administrador no se puede asignar")
        access_role = db.scalar(
            select(AccessRole).where(
                AccessRole.slug == role_slug,
                AccessRole.deleted_at.is_(None),
            )
        )
        if access_role is None:
            raise HTTPException(404, "Rol no encontrado")
        if access_role.slug == "admin":
            raise HTTPException(403, "El rol administrador no se puede asignar")
        if str(item.role) == "admin":
            raise HTTPException(403, "No puedes modificar el rol de un administrador")
        if str(admin.role) != "admin":
            own_permissions = set(
                admin.permission_role.permissions if admin.permission_role else []
            )
            unauthorized = set(access_role.permissions or []) - own_permissions
            if unauthorized:
                raise HTTPException(
                    403,
                    "No puedes asignar un rol con permisos que no tienes autorizados: "
                    + ", ".join(sorted(unauthorized)),
                )
        item.permission_role = access_role
        item.role = (
            role_slug if role_slug in {"admin", "operador", "chofer", "cliente"} else "operador"
        )
    client_id = payload.get("client_id", item.data.get("client_id"))
    if "client_id" in payload and not has_permission(
        admin, "usuarios.asignar_roles", db, request
    ):
        raise HTTPException(403, "No tienes permiso para vincular un cliente")
    if str(item.role) != "cliente" and "client_id" not in payload:
        client_id = None
    if str(item.role) == "cliente" and not client_id:
        raise HTTPException(422, "Selecciona un cliente para esta cuenta")
    if client_id and str(item.role) != "cliente":
        raise HTTPException(400, "Solo los usuarios cliente pueden vincularse a un cliente")
    linked_client = db.get(Client, client_id) if client_id else None
    if client_id and (linked_client is None or linked_client.deleted_at is not None):
        raise HTTPException(404, "Cliente no encontrado")
    if "active" in payload:
        if not isinstance(payload["active"], bool):
            raise HTTPException(422, "El estado activo debe ser verdadero o falso")
        if not payload["active"] and str(item.role) == "admin":
            remaining = db.scalar(
                select(func.count()).select_from(User).where(
                    User.role == "admin",
                    User.active.is_(True),
                    User.deleted_at.is_(None),
                )
            ) or 0
            if remaining <= 1:
                raise HTTPException(409, "No se puede desactivar al último administrador")
        item.active = bool(payload["active"])
    if "password" in payload:
        if len(str(payload["password"])) < 8 or len(str(payload["password"]).encode("utf-8")) > 72:
            raise HTTPException(400, "La contraseña debe tener entre 8 y 72 bytes")
        item.password_hash = hash_password(str(payload["password"]))
    item.data = {
        **item.data,
        **{key: payload[key] for key in ("name", "client_id") if key in payload},
    }
    if str(item.role) != "cliente":
        item.data.pop("client_id", None)
    if "role" in payload or client_id != previous_client_id:
        db.add(
            AccessRoleAudit(
                role_id=item.permission_role_id,
                actor_email=admin.email,
                action="asignar_rol" if "role" in payload else "vincular_cliente",
                details={
                    "user_id": item.id,
                    "user_email": item.email,
                    "previous_role_id": previous_role_id,
                    "role_id": item.permission_role_id,
                    "previous_client_id": previous_client_id,
                    "client_id": item.data.get("client_id"),
                    "source": "editar_usuario",
                },
                created_by=admin.id,
                data={},
            )
        )
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "email": item.email,
        "role": item.permission_role.slug if item.permission_role else item.role,
        "role_name": _role_name(item),
        "active": item.active,
        "data": item.data,
        "permission_role_id": item.permission_role_id,
    }


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))
):
    item = db.get(User, user_id)
    if not item or item.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    if str(item.role) == "admin":
        if str(admin.role) != "admin":
            raise HTTPException(403, "No puedes eliminar la cuenta de un administrador")
        remaining = db.scalar(
            select(func.count()).select_from(User).where(
                User.role == "admin",
                User.active.is_(True),
                User.deleted_at.is_(None),
            )
        ) or 0
        if remaining <= 1:
            raise HTTPException(409, "No se puede eliminar al último administrador")
    item.active = False
    item.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None
