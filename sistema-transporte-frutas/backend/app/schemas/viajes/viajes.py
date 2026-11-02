from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from app.models.enums import TripStatus


class ViajeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, min_length=1, max_length=40)
    vehiculo_id: str
    conductor_id: str
    ruta_id: str
    fecha_salida_programada: datetime
    fecha_entrega_estimada: datetime
    cargas_ids: list[str] = Field(default_factory=list)
    flete_centimos: int | None = Field(default=None, ge=0)
    moneda: Literal["PEN"] = "PEN"

    @field_validator("fecha_salida_programada", "fecha_entrega_estimada")
    @classmethod
    def normalize_timezone(cls, value):
        if value is None:
            return value
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.fecha_entrega_estimada <= self.fecha_salida_programada:
            raise ValueError(
                "La fecha estimada de entrega debe ser posterior a la salida programada."
            )
        if len(self.cargas_ids) != len(set(self.cargas_ids)):
            raise ValueError("No se puede asignar la misma carga más de una vez.")
        return self


class ViajeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, min_length=1, max_length=40)
    vehiculo_id: str | None = None
    conductor_id: str | None = None
    ruta_id: str | None = None
    fecha_salida_programada: datetime | None = None
    fecha_entrega_estimada: datetime | None = None
    flete_centimos: int | None = Field(default=None, ge=0)
    moneda: Literal["PEN"] | None = None

    @field_validator("fecha_salida_programada", "fecha_entrega_estimada")
    @classmethod
    def normalize_timezone(cls, value):
        if value is None:
            return value
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )


class ViajeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    codigo: str
    vehiculo_id: str | None
    conductor_id: str | None
    ruta_id: str | None
    estado: TripStatus
    fecha_salida_programada: datetime
    fecha_entrega_estimada: datetime
    salida_real: datetime | None = None
    entrega_real: datetime | None = None
    flete_centimos: int | None = None
    moneda: str = "PEN"
    etapas: list[dict] = Field(default_factory=list)
    cargas_ids: list[str] = Field(default_factory=list)
    peso_total_kg: Decimal | None = None
    capacidad_kg: int | None = None
    peso_incompleto: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None


class ViajeTransicion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: TripStatus


class ViajeCargasUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cargas_ids: list[str]
    motivo: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def unique_loads(self):
        if len(self.cargas_ids) != len(set(self.cargas_ids)):
            raise ValueError("No se puede asignar la misma carga más de una vez.")
        return self
