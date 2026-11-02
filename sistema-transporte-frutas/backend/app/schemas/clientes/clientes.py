from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

TipoDocumento = Literal["RUC", "DNI", "CE"]
TipoCliente = Literal["Empresa", "Persona natural"]
EstadoCliente = Literal["activo", "inactivo"]


class ClienteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=255)
    documento: str = Field(min_length=8, max_length=30)
    tipo_documento: TipoDocumento
    tipo: TipoCliente
    estado: EstadoCliente = "activo"
    nombre_comercial: str | None = Field(default=None, max_length=255)
    telefono: str = Field(min_length=6, max_length=20, pattern=r"^\+?[0-9][0-9 ()-]*$")
    correo: EmailStr | None = None
    departamento: str = Field(min_length=1, max_length=100)
    ubicacion: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=255)
    contacto: str | None = Field(default=None, max_length=150)
    notas: str | None = Field(default=None, max_length=2000)

    @field_validator("nombre", "departamento", mode="before")
    @classmethod
    def trim_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("documento", mode="before")
    @classmethod
    def normalize_document(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("telefono", mode="before")
    @classmethod
    def trim_phone(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("correo", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value.lower() or None
        return value

    @model_validator(mode="after")
    def validate_document_format(self):
        validate_document(self.tipo_documento, self.documento)
        validate_phone(self.telefono)
        return self


class ClienteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=255)
    documento: str | None = Field(default=None, min_length=8, max_length=30)
    tipo_documento: TipoDocumento | None = None
    tipo: TipoCliente | None = None
    estado: EstadoCliente | None = None
    nombre_comercial: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(
        default=None, min_length=6, max_length=20, pattern=r"^\+?[0-9][0-9 ()-]*$"
    )
    correo: EmailStr | None = None
    departamento: str | None = Field(default=None, min_length=1, max_length=100)
    ubicacion: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=255)
    contacto: str | None = Field(default=None, max_length=150)
    notas: str | None = Field(default=None, max_length=2000)

    @field_validator("nombre", "departamento", mode="before")
    @classmethod
    def trim_optional_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("documento", mode="before")
    @classmethod
    def normalize_optional_document(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("telefono", mode="before")
    @classmethod
    def trim_optional_phone(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("correo", mode="before")
    @classmethod
    def normalize_optional_email(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value.lower() or None
        return value

    @model_validator(mode="after")
    def validate_document_format_when_type_is_known(self):
        required_if_set = (
            "nombre",
            "documento",
            "tipo_documento",
            "tipo",
            "estado",
            "telefono",
            "departamento",
        )
        null_required = [
            field
            for field in required_if_set
            if field in self.model_fields_set and getattr(self, field) is None
        ]
        if null_required:
            raise ValueError(f"Estos campos no pueden ser nulos: {', '.join(null_required)}")
        if self.documento is not None and self.tipo_documento is not None:
            validate_document(self.tipo_documento, self.documento)
        if self.telefono is not None:
            validate_phone(self.telefono)
        return self


class ClienteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nombre: str = Field(max_length=255)
    documento: str | None = Field(default=None, max_length=30)
    tipo_documento: TipoDocumento | None = None
    tipo: TipoCliente | None = None
    estado: EstadoCliente
    nombre_comercial: str | None = None
    telefono: str | None = None
    correo: str | None = None
    departamento: str | None = None
    ubicacion: str | None = None
    direccion: str | None = None
    contacto: str | None = None
    notas: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: str | None = None


class ClienteHistoryEntry(BaseModel):
    carga_id: str | None = None
    retorno_id: str | None = None
    jabas: int
    fecha: datetime | None = None


class ClienteCrateHistoryResponse(BaseModel):
    cliente_id: str
    despachos: list[ClienteHistoryEntry]
    retornos: list[ClienteHistoryEntry]
    saldo_pendiente: int


def validate_document(document_type: TipoDocumento, document: str) -> None:
    digits = sum(character.isdigit() for character in document)
    if document_type == "RUC" and (len(document) != 11 or not document.isdigit()):
        raise ValueError("El RUC debe tener 11 dígitos")
    if document_type == "DNI" and (len(document) != 8 or not document.isdigit()):
        raise ValueError("El DNI debe tener 8 dígitos")
    if document_type == "CE" and (
        not 8 <= len(document) <= 12 or digits < 6 or not document.isalnum()
    ):
        raise ValueError("El CE debe tener entre 8 y 12 caracteres alfanuméricos")


def validate_phone(phone: str) -> None:
    digits = sum(character.isdigit() for character in phone)
    if not 6 <= digits <= 15:
        raise ValueError("El teléfono debe contener entre 6 y 15 dígitos")
