from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RouteStatus = Literal["activa", "inactiva"]
RouteCurrency = Literal["PEN"]


class ParadaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ciudad_id: int = Field(gt=0)
    orden: int = Field(gt=0)
    tiempo_espera: int = Field(default=0, ge=0, le=1000000)


class ParadaResponse(ParadaInput):
    id_parada: int
    ciudad: str


class RutaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(pattern=r"^R-\d{3}$", min_length=5, max_length=5)
    nombre: str = Field(min_length=2, max_length=255)
    origen_id: int = Field(gt=0)
    destino_id: int = Field(gt=0)
    estado: RouteStatus = "activa"
    distancia_km: Decimal = Field(gt=0, le=Decimal("999999.999"), max_digits=12, decimal_places=3)
    duracion_minutos: int = Field(gt=0, le=1000000)
    peajes_minor: int = Field(default=0, ge=0, le=10**15)
    tarifa_referencial_minor: int = Field(default=0, ge=0, le=10**15)
    moneda: RouteCurrency = "PEN"
    paradas: list[ParadaInput] = Field(default_factory=list, max_length=50)
    notas: str | None = Field(default=None, max_length=2000)

    @field_validator("codigo", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("nombre", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RutaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, pattern=r"^R-\d{3}$", min_length=5, max_length=5)
    nombre: str | None = Field(default=None, min_length=2, max_length=255)
    origen_id: int | None = Field(default=None, gt=0)
    destino_id: int | None = Field(default=None, gt=0)
    estado: RouteStatus | None = None
    distancia_km: Decimal | None = Field(
        default=None, gt=0, le=Decimal("999999.999"), max_digits=12, decimal_places=3
    )
    duracion_minutos: int | None = Field(default=None, gt=0, le=1000000)
    peajes_minor: int | None = Field(default=None, ge=0, le=10**15)
    tarifa_referencial_minor: int | None = Field(default=None, ge=0, le=10**15)
    moneda: RouteCurrency | None = None
    paradas: list[ParadaInput] | None = Field(default=None, max_length=50)
    notas: str | None = Field(default=None, max_length=2000)

    @field_validator("codigo", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("nombre", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = {
            "codigo",
            "nombre",
            "origen_id",
            "destino_id",
            "estado",
            "distancia_km",
            "duracion_minutos",
            "moneda",
        }
        nulls = [
            key for key in required if key in self.model_fields_set and getattr(self, key) is None
        ]
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(sorted(nulls))}")
        return self


class RutaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    codigo: str
    nombre: str
    origen: str
    destino: str
    origen_id: int
    destino_id: int
    estado: RouteStatus
    distancia_km: Decimal | None = None
    duracion_minutos: int | None = None
    peajes_minor: int | None = None
    tarifa_referencial_minor: int | None = None
    moneda: RouteCurrency
    paradas: list[ParadaResponse] = Field(default_factory=list)
    notas: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
