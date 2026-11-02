"""Typed response contracts for API resources and aggregate endpoints."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.cargas.cargas import CargaResponse as CargasResponse
from app.schemas.clientes.clientes import ClienteResponse
from app.schemas.conductores.conductores import ConductorResponse as ConductoresResponse
from app.schemas.rutas.rutas import RutaResponse as RutasResponse
from app.schemas.vehiculos.vehiculos import VehiculoResponse as VehiculosResponse
from app.schemas.viajes.viajes import ViajeResponse as ViajesResponse
from app.schemas.cotizaciones.cotizaciones import CotizacionResponse as CotizacionesResponse

T = TypeVar("T")


class CodeSuggestionResponse(BaseModel):
    code: str


class ResourceResponse(BaseModel):
    """Flattened resource returned by the generic records API."""

    model_config = ConfigDict(extra="allow")
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None


class ClientesResponse(ResourceResponse):
    pass


class RetornosResponse(ResourceResponse):
    total_jabas_retornadas: int | None = None


class DocumentosResponse(ResourceResponse):
    pass


class GastosResponse(ResourceResponse):
    pass


class CombustibleResponse(ResourceResponse):
    pass


class MantenimientoResponse(ResourceResponse):
    pass


class PagosResponse(ResourceResponse):
    pass


class ConfiguracionResponse(ResourceResponse):
    pass


class UsuarioResponse(BaseModel):
    """Public user fields only; authentication secrets are never serialized."""

    id: str
    email: str
    role: str
    active: bool
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    # Kept during the transition for existing frontend consumers.
    pages: int


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Any | None = None


class DashboardReportResponse(BaseModel):
    clientes: int
    cargas: int
    cargas_en_transito: int
    viajes: int
    retornos: int


class TripProfitabilityResponse(BaseModel):
    viaje_id: str
    ingresos_centimos: int
    costos_centimos: int
    utilidad_centimos: int


class FuelConsumptionResponse(BaseModel):
    vehiculo_id: str
    litros: float
    costo_centimos: int


class CrateBalanceResponse(BaseModel):
    cliente_id: str | None
    total_despachadas: int
    total_retornadas: int
    saldo_pendiente: int
    periodo_id: str | None = None


class ReturnBalanceCutResponse(BaseModel):
    id: str
    cliente_id: str
    numero_corte: int
    cliente_nombre: str
    total_despachadas: int
    total_retornadas: int
    saldo_pendiente: int
    fecha: datetime
    usuario_email: str


class PortalProfileResponse(BaseModel):
    id: str
    email: str
    cliente_id: str | None
    nombre: str | None = None


class PortalLoadResponse(ResourceResponse):
    pass


class PortalRouteSummary(BaseModel):
    nombre: str
    origen: str
    destino: str


class PortalTripResponse(BaseModel):
    id: str
    codigo: str
    estado: str
    fecha_salida_programada: datetime | None = None
    fecha_entrega_estimada: datetime | None = None
    salida_real: datetime | None = None
    entrega_real: datetime | None = None
    ruta: PortalRouteSummary | None = None


class PortalDocumentResponse(ResourceResponse):
    pass


class PortalPaymentResponse(ResourceResponse):
    pass


RESOURCE_RESPONSE_MODELS: dict[str, type[ResourceResponse]] = {
    "clientes": ClienteResponse,
    "conductores": ConductoresResponse,
    "vehiculos": VehiculosResponse,
    "rutas": RutasResponse,
    "cargas": CargasResponse,
    "viajes": ViajesResponse,
    "cotizaciones": CotizacionesResponse,
    "retornos": RetornosResponse,
    "documentos": DocumentosResponse,
    "gastos": GastosResponse,
    "combustible": CombustibleResponse,
    "mantenimiento": MantenimientoResponse,
    "pagos": PagosResponse,
    "configuracion": ConfiguracionResponse,
}
