from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.schemas.vehiculos.vehiculos import VehiculoCreate, VehiculoResponse, VehiculoUpdate
from app.services.viajes.viajes import guard_reference_deactivation

router = build_resource_router(
    "vehiculos",
    ResourceContract(
        create_schema=VehiculoCreate,
        update_schema=VehiculoUpdate,
        response_schema=VehiculoResponse,
        search_fields=("fleet_code", "plate", "vin", "data.marca", "data.modelo"),
        filters={"estado": "status", "tipo": "vehicle_type"},
        unique_fields={"codigo_flota": "fleet_code", "placa": "plate", "vin": "vin"},
        column_fields={
            "codigo_flota": "fleet_code",
            "placa": "plate",
            "vin": "vin",
            "tipo": "vehicle_type",
            "capacidad_kg": "capacity_kg",
            "estado": "status",
            "tiene_remolque": "has_trailer",
            "placa_remolque": "trailer_plate",
        },
        permissions={
            "list": ("admin", "operador"),
            "read": ("admin", "operador"),
            "create": ("admin", "operador"),
            "update": ("admin", "operador"),
            "delete": ("admin",),
            "reactivate": ("admin",),
        },
        code_suggestion=("fleet_code", "V", 2, 999),
        allow_reactivate=True,
        delete_guard=lambda db, record_id: guard_reference_deactivation(db, "vehiculos", record_id),
    ),
)
