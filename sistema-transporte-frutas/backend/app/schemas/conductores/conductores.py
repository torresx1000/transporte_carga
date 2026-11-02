from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

DriverStatusInput = Literal["disponible", "descanso", "inactivo"]
DriverStatusResponse = Literal["disponible", "en_viaje", "descanso", "inactivo"]
LicenseCategory = Literal["A-I", "A-IIa", "A-IIb", "A-IIIa", "A-IIIb", "A-IIIc"]


def _trim(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _validate_document(value: str | None) -> str | None:
    if value is not None and not (
        value.isdigit() and len(value) == 8 or value.isalnum() and 8 <= len(value) <= 12
    ):
        raise ValueError(
            "Ingresa un DNI de 8 dígitos o un documento alfanumérico de 8 a 12 caracteres"
        )
    return value


class ConductorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=255)
    documento: str = Field(min_length=8, max_length=12)
    telefono: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9][0-9 ()-]*$")
    correo: EmailStr | None = None
    licencia: str = Field(min_length=5, max_length=50, pattern=r"^[A-Za-z0-9-]+$")
    categoria_licencia: LicenseCategory
    licencia_vence: date | None = None
    examen_medico_vence: date | None = None
    estado: DriverStatusInput = "disponible"

    @field_validator("nombre", "documento", "licencia", "telefono", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _trim(value)

    @field_validator("documento", mode="after")
    @classmethod
    def valid_document(cls, value: str) -> str:
        return _validate_document(value) or value


class ConductorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=255)
    documento: str | None = Field(default=None, min_length=8, max_length=12)
    telefono: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9][0-9 ()-]*$")
    correo: EmailStr | None = None
    licencia: str | None = Field(
        default=None, min_length=5, max_length=50, pattern=r"^[A-Za-z0-9-]+$"
    )
    categoria_licencia: LicenseCategory | None = None
    licencia_vence: date | None = None
    examen_medico_vence: date | None = None
    estado: DriverStatusInput | None = None

    @field_validator("nombre", "documento", "licencia", "telefono", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _trim(value)

    @model_validator(mode="after")
    def validate_required_values(self):
        required = {"nombre", "documento", "licencia", "categoria_licencia", "estado"}
        nulls = [
            key for key in required if key in self.model_fields_set and getattr(self, key) is None
        ]
        if nulls:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(sorted(nulls))}")
        _validate_document(self.documento)
        return self


class ConductorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nombre: str
    documento: str | None = None
    telefono: str | None = None
    correo: str | None = None
    licencia: str | None = None
    categoria_licencia: LicenseCategory | None = None
    licencia_vence: date | None = None
    examen_medico_vence: date | None = None
    estado: DriverStatusResponse
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None
