from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VehicleType = Literal["Camión", "Furgón", "Camioneta", "Tráiler"]
VehicleStatusInput = Literal["disponible", "mantenimiento", "inactivo"]
VehicleStatusResponse = Literal["disponible", "en_viaje", "mantenimiento", "inactivo"]


class VehiculoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_flota: str = Field(pattern=r"^V-\d{2,3}$", min_length=4, max_length=5)
    placa: str = Field(min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]{3}-?[A-Za-z0-9]{3,4}$")
    vin: str | None = Field(
        default=None, min_length=17, max_length=17, pattern=r"^[A-HJ-NPR-Z0-9]{17}$"
    )
    tipo: VehicleType
    capacidad_kg: int = Field(gt=0, le=500000)
    estado: VehicleStatusInput = "disponible"
    tiene_remolque: bool = False
    placa_remolque: str | None = Field(default=None, min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]{3}-?[A-Za-z0-9]{3,4}$")

    @field_validator("codigo_flota", "placa", "vin", "placa_remolque", mode="before")
    @classmethod
    def normalize_identifiers(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_trailer(self):
        if self.tiene_remolque and not self.placa_remolque:
            raise ValueError("La placa del remolque es obligatoria cuando el vehículo tiene remolque")
        if not self.tiene_remolque:
            self.placa_remolque = None
        return self


class VehiculoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_flota: str | None = Field(
        default=None, pattern=r"^V-\d{2,3}$", min_length=4, max_length=5
    )
    placa: str | None = Field(
        default=None, min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]{3}-?[A-Za-z0-9]{3,4}$"
    )
    vin: str | None = Field(
        default=None, min_length=17, max_length=17, pattern=r"^[A-HJ-NPR-Z0-9]{17}$"
    )
    tipo: VehicleType | None = None
    capacidad_kg: int | None = Field(default=None, gt=0, le=500000)
    estado: VehicleStatusInput | None = None
    tiene_remolque: bool | None = None
    placa_remolque: str | None = Field(default=None, min_length=6, max_length=8, pattern=r"^[A-Za-z0-9]{3}-?[A-Za-z0-9]{3,4}$")

    @field_validator("codigo_flota", "placa", "vin", "placa_remolque", mode="before")
    @classmethod
    def normalize_identifiers(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = {"codigo_flota", "placa", "tipo", "capacidad_kg", "estado", "tiene_remolque"}
        nulls = [
            key for key in required if key in self.model_fields_set and getattr(self, key) is None
        ]
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(sorted(nulls))}")
        return self


class VehiculoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    codigo_flota: str
    placa: str
    vin: str | None = None
    tipo: VehicleType | None = None
    capacidad_kg: int | None = None
    estado: VehicleStatusResponse
    tiene_remolque: bool = False
    placa_remolque: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
