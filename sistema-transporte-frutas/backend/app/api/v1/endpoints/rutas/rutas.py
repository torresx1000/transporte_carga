from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.schemas.rutas.rutas import RutaCreate, RutaResponse, RutaUpdate
from app.services.rutas.rutas import RutaService
from app.services.viajes.viajes import guard_reference_deactivation

router = build_resource_router(
    "rutas",
    ResourceContract(
        service_factory=RutaService,
        create_schema=RutaCreate,
        update_schema=RutaUpdate,
        response_schema=RutaResponse,
        search_fields=("code", "name", "origin", "destination"),
        filters={"estado": "status"},
        unique_fields={"codigo": "code"},
        column_fields={
            "codigo": "code",
            "nombre": "name",
            "origen": "origin",
            "destino": "destination",
            "estado": "status",
            "distancia_km": "distance_km",
            "duracion_minutos": "estimated_duration_minutes",
            "peajes_minor": "tolls_minor",
            "tarifa_referencial_minor": "reference_tariff_minor",
            "moneda": "currency",
        },
        permissions={
            "list": ("admin", "operador"),
            "read": ("admin", "operador"),
            "create": ("admin", "operador"),
            "update": ("admin", "operador"),
            "delete": ("admin",),
            "reactivate": ("admin",),
        },
        code_suggestion=("code", "R", 3, 999),
        allow_reactivate=True,
        delete_guard=lambda db, record_id: guard_reference_deactivation(db, "rutas", record_id),
    ),
)
