from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.permissions import require_roles
from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.models.entities import Client, Load, ReturnAllocation, ReturnRecord, User
from app.repositories.clientes.clientes import ClienteRepository
from app.schemas.clientes.clientes import (
    ClienteCreate,
    ClienteCrateHistoryResponse,
    ClienteResponse,
    ClienteUpdate,
)
from app.services.clientes.clientes import ClienteService

CLIENT_CONTRACT = ResourceContract(
    create_schema=ClienteCreate,
    update_schema=ClienteUpdate,
    response_schema=ClienteResponse,
    search_fields=(
        "name",
        "document",
        "data.nombre_comercial",
        "data.telefono",
        "data.correo",
        "data.contacto",
        "data.departamento",
        "data.ubicacion",
    ),
    filters={"estado": "estado", "tipo": "tipo"},
    unique_fields={"documento": "document"},
    permissions={
        "list": ("admin", "operador"),
        "read": ("admin", "operador"),
        "create": ("admin", "operador"),
        "update": ("admin", "operador"),
        "delete": ("admin",),
        "reactivate": ("admin",),
    },
    service_factory=lambda db: ClienteService(ClienteRepository(db)),
    allow_reactivate=True,
)

router = build_resource_router("clientes", CLIENT_CONTRACT)
admin_or_operator = require_roles("admin", "operador")


@router.get("/{client_id}/estado-jabas", response_model=ClienteCrateHistoryResponse)
def client_crate_history(
    client_id: str, db: Session = Depends(get_db), user: User = Depends(admin_or_operator)
):
    client = db.get(Client, client_id)
    if not client or client.deleted_at is not None:
        raise ApiError(404, "CLIENT_NOT_FOUND", "Cliente no encontrado")
    dispatched = db.scalars(
        select(Load).where(Load.client_id == client_id, Load.deleted_at.is_(None))
    ).all()
    allocations = db.scalars(
        select(ReturnAllocation).where(
            ReturnAllocation.client_id == client_id, ReturnAllocation.deleted_at.is_(None)
        )
    ).all()
    parent_ids = {item.return_id for item in allocations}
    legacy_returns = db.scalars(
        select(ReturnRecord).where(
            ReturnRecord.client_id == client_id, ReturnRecord.deleted_at.is_(None)
        )
    ).all()
    return_items = [
        {"retorno_id": item.id, "jabas": item.returned_total, "fecha": item.created_at}
        for item in legacy_returns
        if item.id not in parent_ids
    ]
    return_items.extend(
        {"retorno_id": item.return_id, "jabas": item.returned_total, "fecha": item.created_at}
        for item in allocations
    )
    return {
        "cliente_id": client_id,
        "despachos": [
            {"carga_id": load.id, "jabas": load.jabas_dispatched, "fecha": load.created_at}
            for load in dispatched
        ],
        "retornos": return_items,
        "saldo_pendiente": sum(i.jabas_dispatched for i in dispatched)
        - sum(i["jabas"] for i in return_items),
    }
