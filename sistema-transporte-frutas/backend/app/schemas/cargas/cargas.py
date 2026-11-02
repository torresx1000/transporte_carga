from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import LoadStatus, Priority


class CargaExtras(BaseModel):
    contacto: str | None = Field(default=None, max_length=150)
    telefono: str | None = Field(default=None, max_length=40)
    destinatario: str | None = Field(default=None, max_length=150)
    presentacion: str | None = Field(default=None, max_length=100)
    origen_departamento: str | None = Field(default=None, max_length=100)
    origen_provincia: str | None = Field(default=None, max_length=100)
    origen_distrito: str | None = Field(default=None, max_length=100)
    origen_direccion: str | None = Field(default=None, max_length=255)
    destino_departamento: str | None = Field(default=None, max_length=100)
    destino_provincia: str | None = Field(default=None, max_length=100)
    destino_distrito: str | None = Field(default=None, max_length=100)
    destino_direccion: str | None = Field(default=None, max_length=255)
    temperatura: Decimal | None = Field(default=None, ge=-100, le=100)
    observaciones: str | None = Field(default=None, max_length=4000)


class EtapaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    viaje_id: str
    origen_id: int = Field(gt=0)
    destino_id: int = Field(gt=0)


class PlanEtapas(BaseModel):
    model_config = ConfigDict(extra="forbid")
    etapas: list[EtapaInput] = Field(max_length=30)


class EtapaEstado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: Literal["en_transito", "completado"]


class CargaCreate(CargaExtras):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, min_length=1, max_length=40)
    cliente_id: str
    origen_id: int = Field(gt=0)
    destino_id: int = Field(gt=0)
    jabas_despachadas: int | None = Field(default=None, ge=0)
    producto: str = Field(min_length=1, max_length=100)
    variedad: str | None = Field(default=None, max_length=100)
    cantidad: int = Field(gt=0)
    unidad: Literal["jaba", "caja", "kg"] = "jaba"
    peso_neto_total_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    peso_bruto_total_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    procedencia: str = Field(min_length=1, max_length=255)
    destino: str = Field(min_length=1, max_length=255)
    fecha_recojo: date | None = None
    fecha_entrega: date | None = None
    monto_cobrar_centimos: int | None = Field(default=None, ge=0)
    moneda: Literal["PEN"] = "PEN"
    prioridad: Priority = Priority.NORMAL


class CargaUpdate(CargaExtras):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = Field(default=None, min_length=1, max_length=40)
    cliente_id: str | None = None
    origen_id: int | None = Field(default=None, gt=0)
    destino_id: int | None = Field(default=None, gt=0)
    jabas_despachadas: int | None = Field(default=None, ge=0)
    producto: str | None = Field(default=None, min_length=1, max_length=100)
    variedad: str | None = Field(default=None, max_length=100)
    cantidad: int | None = Field(default=None, gt=0)
    unidad: Literal["jaba", "caja", "kg"] | None = None
    peso_neto_total_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    peso_bruto_total_kg: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    procedencia: str | None = Field(default=None, min_length=1, max_length=255)
    destino: str | None = Field(default=None, min_length=1, max_length=255)
    fecha_recojo: date | None = None
    fecha_entrega: date | None = None
    monto_cobrar_centimos: int | None = Field(default=None, ge=0)
    moneda: Literal["PEN"] | None = None
    prioridad: Priority | None = None
    motivo: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = {
            "codigo",
            "cliente_id",
            "origen_id",
            "destino_id",
            "jabas_despachadas",
            "prioridad",
            "producto",
            "cantidad",
            "unidad",
            "procedencia",
            "destino",
            "moneda",
        }
        nulls = [
            key for key in required if key in self.model_fields_set and getattr(self, key) is None
        ]
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(sorted(nulls))}")
        return self


class CargaResponse(CargaExtras):
    model_config = ConfigDict(extra="forbid")

    origen_id: int | None = None
    destino_id: int | None = None
    etapas: list[dict] = Field(default_factory=list)
    id: str
    codigo: str
    cliente_id: str | None
    periodo_retorno_id: str | None = None
    viaje_id: str | None
    estado: LoadStatus
    prioridad: Priority
    jabas_despachadas: int
    producto: str
    variedad: str | None = None
    cantidad: int
    unidad: str
    peso_neto_total_kg: Decimal | None = None
    peso_bruto_total_kg: Decimal | None = None
    peso_incompleto: bool = False
    procedencia: str
    destino: str
    fecha_recojo: date | None = None
    fecha_entrega: date | None = None
    monto_cobrar_centimos: int | None = None
    moneda: str = "PEN"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None


class CargaEstadoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: LoadStatus
