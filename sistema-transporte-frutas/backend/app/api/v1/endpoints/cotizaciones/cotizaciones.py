from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.schemas.cotizaciones.cotizaciones import (
    CotizacionCreate,
    CotizacionResponse,
    CotizacionUpdate,
)
from app.services.cotizaciones.cotizaciones import CotizacionService


router = build_resource_router(
    "cotizaciones",
    ResourceContract(
        create_schema=CotizacionCreate,
        update_schema=CotizacionUpdate,
        response_schema=CotizacionResponse,
        search_fields=("code",),
        filters={"estado": "status", "cliente_id": "client_id", "ruta_id": "route_id"},
        unique_fields={"codigo": "code"},
        permissions={
            "list": ("admin", "operador"),
            "read": ("admin", "operador"),
            "create": ("admin", "operador"),
            "update": ("admin", "operador"),
            "delete": ("admin",),
        },
        service_factory=CotizacionService,
        prefix="/cotizaciones",
    ),
)
