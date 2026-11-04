import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import (
    get_current_user,
    has_permission,
    permission_catalog,
    permissions_for_user,
    require_any_permission,
    require_permission,
    role_permission_keys,
)
from app.models.entities import Client, User
from app.models.roles import AccessRole, AccessRoleAudit

router = APIRouter(prefix="/roles", tags=["roles"])


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    permissions: list[str] = Field(default_factory=list, max_length=500)


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] | None = Field(default=None, max_length=500)


class RoleAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str | None = None


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    if not slug:
        raise HTTPException(422, "El nombre del rol debe incluir letras o números")
    return slug[:80]


def _role_response(role: AccessRole, db: Session) -> dict[str, Any]:
    members = db.scalars(
        select(User).where(
            User.role == "admin" if role.slug == "admin" else User.permission_role_id == role.id,
            User.deleted_at.is_(None),
        )
    ).all()
    return {
        "id": role.id,
        "slug": role.slug,
        "name": role.name,
        "description": role.description,
        "permissions": role.permissions or [],
        "is_system": role.is_system,
        "users_count": len(members),
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


def _audit(
    db: Session,
    actor: User,
    action: str,
    details: dict[str, Any],
    role_id: str | None = None,
) -> None:
    db.add(
        AccessRoleAudit(
            role_id=role_id,
            actor_email=actor.email,
            action=action,
            details=details,
            created_by=actor.id,
            data={},
        )
    )


def _seed_roles(db: Session, request: Request) -> None:
    catalog = permission_catalog(request)
    default_roles = (
        ("admin", "Administrador", "Acceso completo al sistema.", True),
        ("operador", "Operaciones", "Permisos operativos predeterminados.", True),
        ("chofer", "Conductor", "Rol base para usuarios conductores.", True),
        ("cliente", "Cliente", "Acceso al portal del cliente.", True),
        ("sin-acceso", "Sin acceso", "Usuario sin permisos de acceso.", True),
    )
    roles: dict[str, AccessRole] = {}
    for slug, name, description, is_system in default_roles:
        role = db.scalar(select(AccessRole).where(AccessRole.slug == slug))
        if role is None:
            role = AccessRole(
                slug=slug,
                name=name,
                description=description,
                permissions=role_permission_keys(catalog, slug),
                is_system=is_system,
                created_by=None,
                data={},
            )
            db.add(role)
            db.flush()
        elif slug == "sin-acceso" and role.permissions:
            previous_permissions = list(role.permissions)
            role.permissions = []
            role.updated_at = datetime.now(timezone.utc)
            db.add(
                AccessRoleAudit(
                    role_id=role.id,
                    actor_email="system",
                    action="proteger_rol",
                    details={
                        "slug": slug,
                        "permissions_removed": previous_permissions,
                        "permissions": [],
                        "reason": "El rol Sin acceso no puede tener permisos",
                    },
                    created_by=None,
                    data={},
                )
            )
        roles[slug] = role
    for user in db.scalars(select(User).where(User.deleted_at.is_(None))).all():
        if str(user.role) != "admin" and user.permission_role_id is None:
            matching_role = roles.get(str(user.role))
            if matching_role:
                user.permission_role_id = matching_role.id
    db.commit()


def _check_permission_assignment(
    permissions: list[str], actor: User, db: Session, request: Request
) -> list[str]:
    unique = list(dict.fromkeys(permissions))
    available = {item["key"] for item in permission_catalog(request)}
    unknown = set(unique) - available
    if unknown:
        raise HTTPException(422, f"Permisos no registrados: {', '.join(sorted(unknown))}")
    if str(actor.role) != "admin":
        own = set(permissions_for_user(actor, db, request))
        unauthorized = set(unique) - own
        if unauthorized:
            raise HTTPException(
                403,
                "No puedes asignar permisos que no tienes autorizados: "
                + ", ".join(sorted(unauthorized)),
            )
    return unique


@router.get("/catalog")
def get_permission_catalog(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("roles.ver", "permisos.gestionar")),
):
    _seed_roles(db, request)
    return permission_catalog(request)


@router.get("/me")
def get_my_permissions(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    _seed_roles(db, request)
    db.refresh(actor)
    role = db.get(AccessRole, actor.permission_role_id) if actor.permission_role_id else None
    return {
        "role": role.slug if role else str(actor.role),
        "permissions": permissions_for_user(actor, db, request),
    }


@router.get("")
def list_roles(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("roles.ver", "permisos.gestionar")),
):
    _seed_roles(db, request)
    roles = db.scalars(
        select(AccessRole)
        .where(AccessRole.deleted_at.is_(None))
        .order_by(AccessRole.name)
    ).all()
    return [_role_response(role, db) for role in roles]


@router.post("", status_code=201)
def create_role(
    payload: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("roles.crear")),
):
    _seed_roles(db, request)
    if payload.permissions and not has_permission(actor, "permisos.gestionar", db, request):
        raise HTTPException(403, "No tienes permiso para asignar permisos a roles")
    slug = _slugify(payload.name)
    if db.scalar(select(AccessRole).where(AccessRole.slug == slug)):
        raise HTTPException(409, "Ya existe un rol con ese nombre")
    permissions = _check_permission_assignment(payload.permissions, actor, db, request)
    role = AccessRole(
        slug=slug,
        name=payload.name.strip(),
        description=payload.description.strip(),
        permissions=permissions,
        is_system=False,
        created_by=actor.id,
        data={},
    )
    db.add(role)
    db.flush()
    _audit(db, actor, "crear", {"name": role.name, "permissions": permissions}, role.id)
    db.commit()
    db.refresh(role)
    return _role_response(role, db)


@router.patch("/{role_id}")
def update_role(
    role_id: str,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("roles.editar", "permisos.gestionar")),
):
    role = db.get(AccessRole, role_id)
    if not role or role.deleted_at:
        raise HTTPException(404, "Rol no encontrado")
    if role.slug in {"admin", "sin-acceso"}:
        raise HTTPException(403, "Este rol protegido no se puede modificar")
    if actor.permission_role_id == role.id and str(actor.role) != "admin":
        raise HTTPException(403, "No puedes modificar los permisos del rol que tienes asignado")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _role_response(role, db)
    if any(key in changes for key in ("name", "description")) and not has_permission(
        actor, "roles.editar", db, request
    ):
        raise HTTPException(403, "No tienes permiso para editar roles")
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    if "name" in changes and changes["name"] is not None:
        before["name"] = role.name
        role.name = changes["name"].strip()
        after["name"] = role.name
    if "description" in changes and changes["description"] is not None:
        before["description"] = role.description
        role.description = changes["description"].strip()
        after["description"] = role.description
    if "permissions" in changes and changes["permissions"] is not None:
        if not has_permission(actor, "permisos.gestionar", db, request):
            raise HTTPException(403, "No tienes permiso para asignar permisos a roles")
        requested = _check_permission_assignment(changes["permissions"], actor, db, request)
        before["permissions"] = role.permissions or []
        role.permissions = requested
        after["permissions"] = requested
    if "name" in after:
        next_slug = _slugify(after["name"])
        duplicate = db.scalar(
            select(AccessRole).where(AccessRole.slug == next_slug, AccessRole.id != role.id)
        )
        if duplicate:
            raise HTTPException(409, "Ya existe un rol con ese nombre")
        if role.slug not in {"admin", "operador", "chofer", "cliente"}:
            before["slug"] = role.slug
            role.slug = next_slug
            after["slug"] = next_slug
    role.updated_at = datetime.now(timezone.utc)
    _audit(db, actor, "editar", {"antes": before, "despues": after}, role.id)
    db.commit()
    db.refresh(role)
    return _role_response(role, db)


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("roles.eliminar")),
):
    role = db.get(AccessRole, role_id)
    if not role or role.deleted_at:
        raise HTTPException(404, "Rol no encontrado")
    if role.is_system or role.slug in {"admin", "sin-acceso"}:
        raise HTTPException(403, "Los roles del sistema no se pueden eliminar")
    if actor.permission_role_id == role.id:
        raise HTTPException(403, "No puedes eliminar el rol que tienes asignado")
    assigned = db.scalar(
        select(User.id).where(
            User.permission_role_id == role.id,
            User.deleted_at.is_(None),
        ).limit(1)
    )
    if assigned:
        raise HTTPException(409, "Asigna otro rol a sus usuarios antes de eliminarlo")
    role.deleted_at = datetime.now(timezone.utc)
    _audit(db, actor, "eliminar", {"name": role.name}, role.id)
    db.commit()
    return None


@router.get("/assignable")
def list_assignable_roles(
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("usuarios.asignar_roles")),
):
    _seed_roles(db, request)
    roles = db.scalars(
        select(AccessRole)
        .where(
            AccessRole.deleted_at.is_(None),
            AccessRole.slug != "admin",
        )
        .order_by(AccessRole.name)
    ).all()
    if str(actor.role) != "admin":
        own_permissions = set(permissions_for_user(actor, db, request))
        roles = [
            role
            for role in roles
            if set(role.permissions or []).issubset(own_permissions)
        ]
    return [
        {"id": role.id, "slug": role.slug, "name": role.name}
        for role in roles
    ]


@router.get("/users")
def list_assignable_users(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("usuarios.asignar_roles")),
):
    users = db.scalars(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.email)
    ).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "name": (user.data or {}).get("name", ""),
            "role": str(user.role),
            "permission_role_id": user.permission_role_id,
            "is_admin": str(user.role) == "admin",
        }
        for user in users
    ]


@router.get("/clients")
def list_assignable_clients(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("usuarios.asignar_roles")),
):
    clients = db.scalars(
        select(Client)
        .where(Client.deleted_at.is_(None))
        .order_by(Client.name)
    ).all()
    return [
        {"id": client.id, "name": client.name, "document": client.document}
        for client in clients
    ]


@router.get("/{role_id}/users")
def list_role_users(
    role_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("roles.ver", "permisos.gestionar")),
):
    role = db.get(AccessRole, role_id)
    if not role or role.deleted_at:
        raise HTTPException(404, "Rol no encontrado")
    users = db.scalars(
        select(User)
        .where(
            User.role == "admin" if role.slug == "admin" else User.permission_role_id == role.id,
            User.deleted_at.is_(None),
        )
        .order_by(User.email)
    ).all()
    return [{"id": user.id, "email": user.email, "name": (user.data or {}).get("name", "")} for user in users]


@router.put("/{role_id}/users/{user_id}")
def assign_role(
    role_id: str,
    user_id: str,
    request: Request,
    payload: RoleAssignment | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("usuarios.asignar_roles")),
):
    role = db.get(AccessRole, role_id)
    target = db.get(User, user_id)
    if not role or role.deleted_at:
        raise HTTPException(404, "Rol no encontrado")
    if not target or target.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    if actor.id == target.id:
        raise HTTPException(403, "No puedes cambiar tu propio rol")
    if str(target.role) == "admin" or role.slug == "admin":
        raise HTTPException(403, "El rol administrador no se puede asignar ni modificar")
    client = None
    if role.slug == "cliente":
        client_id = payload.client_id if payload else None
        if not client_id:
            raise HTTPException(422, "Selecciona el cliente que se vinculará a esta cuenta")
        client = db.scalar(
            select(Client).where(
                Client.id == client_id,
                Client.deleted_at.is_(None),
            )
        )
        if client is None:
            raise HTTPException(404, "Cliente no encontrado")
    elif payload and payload.client_id:
        raise HTTPException(422, "Solo una cuenta con rol Cliente puede vincularse a un cliente")
    if str(actor.role) != "admin":
        own_permissions = set(permissions_for_user(actor, db, request))
        unauthorized = set(role.permissions or []) - own_permissions
        if unauthorized:
            raise HTTPException(
                403,
                "No puedes asignar un rol con permisos que no tienes autorizados: "
                + ", ".join(sorted(unauthorized)),
            )
    if target.permission_role_id == role.id:
        if role.slug != "cliente" or target.data.get("client_id") == client.id:
            return {"user_id": target.id, "role_id": role.id}
    previous_role_id = target.permission_role_id
    previous_client_id = (target.data or {}).get("client_id")
    target.permission_role_id = role.id
    if role.slug in {"admin", "operador", "chofer", "cliente"}:
        target.role = role.slug
    elif str(target.role) == "cliente":
        target.role = "operador"
    target.data = {**(target.data or {})}
    if role.slug == "cliente":
        target.data["client_id"] = client.id
    else:
        target.data.pop("client_id", None)
    _audit(
        db,
        actor,
        "asignar_rol",
        {
            "user_id": target.id,
            "email": target.email,
            "previous_role_id": previous_role_id,
            "previous_client_id": previous_client_id,
            "client_id": client.id if client else None,
        },
        role.id,
    )
    db.commit()
    return {"user_id": target.id, "role_id": role.id}


@router.delete("/{role_id}/users/{user_id}", status_code=204)
def unassign_role(
    role_id: str,
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("usuarios.asignar_roles")),
):
    _seed_roles(db, request)
    role = db.get(AccessRole, role_id)
    target = db.get(User, user_id)
    if not role or role.deleted_at:
        raise HTTPException(404, "Rol no encontrado")
    if not target or target.deleted_at:
        raise HTTPException(404, "Usuario no encontrado")
    if actor.id == target.id:
        raise HTTPException(403, "No puedes cambiar tu propio rol")
    if str(target.role) == "admin":
        raise HTTPException(403, "No puedes retirar el rol de un administrador")
    if target.permission_role_id != role.id:
        raise HTTPException(409, "El usuario no tiene asignado ese rol")
    if str(actor.role) != "admin":
        own_permissions = set(permissions_for_user(actor, db, request))
        unauthorized = set(role.permissions or []) - own_permissions
        if unauthorized:
            raise HTTPException(
                403,
                "No puedes administrar este rol porque contiene permisos fuera de tu alcance: "
                + ", ".join(sorted(unauthorized)),
            )
    no_access_role = db.scalar(
        select(AccessRole).where(
            AccessRole.slug == "sin-acceso",
            AccessRole.deleted_at.is_(None),
        )
    )
    if no_access_role is None:
        raise HTTPException(500, "No se encontró el rol protegido sin acceso")
    target.permission_role_id = no_access_role.id
    _audit(
        db,
        actor,
        "retirar_rol",
        {"user_id": target.id, "email": target.email, "previous_role_id": role.id},
        no_access_role.id,
    )
    db.commit()
    return None


@router.get("/audit")
def list_role_audit(
    db: Session = Depends(get_db),
    actor: User = Depends(require_any_permission("roles.ver", "permisos.gestionar")),
):
    events = db.scalars(
        select(AccessRoleAudit)
        .order_by(AccessRoleAudit.created_at.desc())
        .limit(200)
    ).all()
    return [
        {
            "id": item.id,
            "role_id": item.role_id,
            "actor_email": item.actor_email,
            "action": item.action,
            "details": item.details,
            "created_at": item.created_at,
        }
        for item in events
    ]
