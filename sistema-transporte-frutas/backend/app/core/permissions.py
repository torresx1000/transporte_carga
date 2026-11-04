import re
from collections.abc import Iterable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import decode_token
from app.models.entities import User
from app.models.roles import AccessRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

ACTION_LABELS = {
    "ver": "Consultar",
    "crear": "Crear",
    "editar": "Editar",
    "eliminar": "Eliminar",
    "cambiar": "Cambiar",
}
SPECIAL_PERMISSIONS = {
    "roles.ver": ("Roles", "Consultar roles"),
    "roles.crear": ("Roles", "Crear roles"),
    "roles.editar": ("Roles", "Editar roles"),
    "roles.eliminar": ("Roles", "Eliminar roles"),
    "permisos.gestionar": ("Roles", "Asignar y retirar permisos"),
    "usuarios.asignar_roles": ("Usuarios", "Asignar roles a usuarios"),
}
EXCLUDED_DEFAULT_MODULES = {"auth", "usuarios", "roles", "configuracion"}


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        user_id = decode_token(token)["sub"]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = db.get(User, user_id)
    if user is None or not user.active or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")
    return user


def _action_for_method(method: str, suffix: str) -> str:
    if suffix:
        if "estado" in suffix.split("_"):
            return f"cambiar_{suffix}"
        prefix = {
            "GET": "ver",
            "POST": "crear",
            "PUT": "editar",
            "PATCH": "editar",
            "DELETE": "eliminar",
        }.get(method, "ver")
        return f"{prefix}_{suffix}"
    return {
        "GET": "ver",
        "POST": "crear",
        "PUT": "editar",
        "PATCH": "editar",
        "DELETE": "eliminar",
    }.get(method, "ver")


def permission_for_route(path: str, method: str) -> str | None:
    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) < 3 or parts[0] != "api" or parts[1] != "v1":
        return None
    module = parts[2]
    suffix_parts = [part for part in parts[3:] if not (part.startswith("{") and part.endswith("}"))]
    suffix = "_".join(re.sub(r"[^a-zA-Z0-9_]", "", part).lower() for part in suffix_parts)
    action = _action_for_method(method.upper(), suffix)
    return f"{module}.{action}"


def permission_catalog(request: Request) -> list[dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    schema = request.app.openapi()
    for path, operations in schema.get("paths", {}).items():
        path_parts = [part for part in path.strip("/").split("/") if part]
        if len(path_parts) < 3 or path_parts[:2] != ["api", "v1"]:
            continue
        module = path_parts[2]
        if module == "auth":
            continue
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            module_label = next(iter(operation.get("tags", [])), module.replace("_", " ").title())
            code = permission_for_route(path, method)
            if code:
                action = code.split(".", 1)[1]
                entries[code] = {
                    "key": code,
                    "module": module,
                    "module_label": module_label,
                    "label": _permission_label(action),
                }
    for key, (module_label, label) in SPECIAL_PERMISSIONS.items():
        module = key.split(".", 1)[0]
        entries[key] = {
            "key": key,
            "module": module,
            "module_label": module_label,
            "label": label,
        }
    return sorted(entries.values(), key=lambda item: (item["module_label"].casefold(), item["label"].casefold()))


def _permission_label(action: str) -> str:
    parts = action.split("_")
    prefix = ACTION_LABELS.get(parts[0], parts[0].replace("-", " ").title())
    suffix = " ".join(part.replace("-", " ").title() for part in parts[1:])
    return f"{prefix} {suffix}".strip()


def role_permission_keys(catalog: Iterable[dict[str, str]], role_slug: str) -> list[str]:
    keys = [item["key"] for item in catalog]
    if role_slug == "admin":
        return keys
    if role_slug == "operador":
        return [
            key
            for key in keys
            if key.split(".", 1)[0] not in EXCLUDED_DEFAULT_MODULES
            and key not in {"permisos.gestionar", "usuarios.asignar_roles"}
        ]
    if role_slug == "cliente":
        return [key for key in keys if key.startswith("portal.")]
    return []


def _is_client_account(user: User, db: Session) -> bool:
    if str(user.role) == "cliente":
        return True
    role = db.get(AccessRole, user.permission_role_id) if user.permission_role_id else None
    return bool(role and role.deleted_at is None and role.slug == "cliente")


def permissions_for_user(user: User, db: Session, request: Request) -> list[str]:
    catalog = permission_catalog(request)
    if str(user.role) == "admin":
        return [item["key"] for item in catalog]
    role = db.get(AccessRole, user.permission_role_id) if user.permission_role_id else None
    if role and role.deleted_at is None:
        if role.slug == "sin-acceso":
            return []
        allowed = set(role.permissions or [])
        if _is_client_account(user, db):
            allowed = {permission for permission in allowed if permission.startswith("portal.")}
        return [item["key"] for item in catalog if item["key"] in allowed]
    if user.role in {"operador", "cliente", "chofer"}:
        return role_permission_keys(catalog, str(user.role))
    return []


def has_permission(user: User, permission: str, db: Session, request: Request) -> bool:
    if str(user.role) == "admin":
        return True
    return permission in permissions_for_user(user, db, request)


def require_permission(permission: str):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        if not has_permission(user, permission, db, request):
            raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción")
        return user

    return dependency


def require_any_permission(*permissions: str):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        if not any(has_permission(user, permission, db, request) for permission in permissions):
            raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción")
        return user

    return dependency


def require_roles(*roles: str):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> User:
        if str(user.role) == "admin":
            return user
        role = db.get(AccessRole, user.permission_role_id) if user.permission_role_id else None
        if role and role.deleted_at is None:
            route = request.scope.get("route")
            permission = permission_for_route(
                getattr(route, "path", ""), request.method
            ) or permission_for_route(request.url.path, request.method)
            if permission and has_permission(user, permission, db, request):
                return user
        elif user.role in roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para realizar esta acción",
        )

    return dependency
