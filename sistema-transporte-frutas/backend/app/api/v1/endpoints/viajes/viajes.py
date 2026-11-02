from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.entities import User
from app.schemas.viajes.viajes import (
    ViajeCargasUpdate,
    ViajeCreate,
    ViajeResponse,
    ViajeTransicion,
    ViajeUpdate,
)
from app.services.viajes.viajes import ViajeService


router = build_resource_router(
    "viajes",
    ResourceContract(
        create_schema=ViajeCreate,
        update_schema=ViajeUpdate,
        response_schema=ViajeResponse,
        search_fields=("code",),
        filters={
            "estado": "status",
            "ruta_id": "route_id",
            "vehiculo_id": "vehicle_id",
            "conductor_id": "driver_id",
        },
        unique_fields={"codigo": "code"},
        column_fields={
            "codigo": "code",
            "vehiculo_id": "vehicle_id",
            "conductor_id": "driver_id",
            "ruta_id": "route_id",
            "estado": "status",
            "fecha_salida_programada": "scheduled_start_at",
            "fecha_entrega_estimada": "scheduled_end_at",
            "salida_real": "actual_start_at",
            "entrega_real": "actual_end_at",
            "flete_centimos": "freight_amount_minor",
            "moneda": "currency",
        },
        permissions={
            "list": ("admin", "operador"),
            "read": ("admin", "operador"),
            "create": ("admin", "operador"),
            "update": ("admin", "operador"),
            "delete": ("admin",),
        },
        service_factory=ViajeService,
        update_actor_context=True,
        prefix="/viajes",
    ),
)


@router.put("/{trip_id}/cargas", response_model=ViajeResponse)
def set_trip_loads(
    trip_id: str,
    payload: ViajeCargasUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    return ViajeService(db).set_loads(trip_id, payload, user.id, user.role)


@router.post("/{trip_id}/estado", response_model=ViajeResponse)
def transition_trip(
    trip_id: str,
    payload: ViajeTransicion,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    return ViajeService(db).transition(trip_id, payload)
