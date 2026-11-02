from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CotizacionLineaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: str = Field(min_length=1, max_length=255)
    cantidad: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    precio_unitario_centimos: int = Field(ge=0)
    orden: int = Field(ge=0)


class CotizacionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str | None = Field(default=None, min_length=1, max_length=40)
    cliente_id: str
    ruta_id: str
    estado: str = "borrador"
    fecha_emision: date
    valida_hasta: date
    descuento_tasa_bps: int = Field(default=0, ge=0, le=10000)
    impuesto_tasa_bps: int = Field(default=0, ge=0, le=10000)
    lineas: list[CotizacionLineaInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dates_state_order(self):
        if self.valida_hasta <= self.fecha_emision:
            raise ValueError("La vigencia debe ser posterior a la fecha de emisión.")
        if self.estado not in {
            "borrador",
            "enviada",
            "aprobada",
            "rechazada",
            "convertida_a_carga",
        }:
            raise ValueError("Estado de cotización no permitido.")
        if len({line.orden for line in self.lineas}) != len(self.lineas):
            raise ValueError("El orden de las líneas no puede repetirse.")
        return self


class CotizacionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: str | None = None
    fecha_emision: date | None = None
    valida_hasta: date | None = None
    descuento_tasa_bps: int | None = Field(default=None, ge=0, le=10000)
    impuesto_tasa_bps: int | None = Field(default=None, ge=0, le=10000)
    lineas: list[CotizacionLineaInput] | None = None

    @model_validator(mode="after")
    def validate_state(self):
        if self.estado is not None and self.estado not in {
            "borrador",
            "enviada",
            "aprobada",
            "rechazada",
            "convertida_a_carga",
        }:
            raise ValueError("Estado de cotización no permitido.")
        if self.fecha_emision and self.valida_hasta and self.valida_hasta <= self.fecha_emision:
            raise ValueError("La vigencia debe ser posterior a la fecha de emisión.")
        if self.lineas is not None and len({line.orden for line in self.lineas}) != len(
            self.lineas
        ):
            raise ValueError("El orden de las líneas no puede repetirse.")
        return self


class CotizacionLineaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: str
    cantidad: Decimal
    precio_unitario_centimos: int
    orden: int
    importe_centimos: int


class CotizacionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    codigo: str
    cliente_id: str | None
    ruta_id: str | None
    estado: str
    fecha_emision: date
    valida_hasta: date
    moneda: str = "PEN"
    descuento_tasa_bps: int
    descuento_centimos: int
    impuesto_tasa_bps: int
    subtotal_centimos: int
    impuesto_centimos: int
    total_centimos: int
    lineas: list[CotizacionLineaResponse]
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
