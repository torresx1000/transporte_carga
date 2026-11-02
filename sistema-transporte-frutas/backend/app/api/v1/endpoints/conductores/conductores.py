from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.schemas.conductores.conductores import ConductorCreate, ConductorResponse, ConductorUpdate
from app.services.viajes.viajes import guard_reference_deactivation

router = build_resource_router(
    "conductores",
    ResourceContract(
        create_schema=ConductorCreate,
        update_schema=ConductorUpdate,
        response_schema=ConductorResponse,
        search_fields=("name", "document", "license_number", "data.telefono", "data.correo"),
        filters={"estado": "status"},
        unique_fields={"documento": "document", "licencia": "license_number"},
        column_fields={
            "nombre": "name",
            "documento": "document",
            "estado": "status",
            "licencia": "license_number",
            "categoria_licencia": "license_category",
            "licencia_vence": "license_expires_at",
            "examen_medico_vence": "medical_exam_expires_at",
        },
        permissions={
            "list": ("admin", "operador"),
            "read": ("admin", "operador"),
            "create": ("admin", "operador"),
            "update": ("admin", "operador"),
            "delete": ("admin",),
            "reactivate": ("admin",),
        },
        allow_reactivate=True,
        delete_guard=lambda db, record_id: guard_reference_deactivation(
            db, "conductores", record_id
        ),
    ),
)
