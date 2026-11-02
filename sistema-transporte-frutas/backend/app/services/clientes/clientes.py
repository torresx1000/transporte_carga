from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.core.errors import ApiError
from app.models.entities import Client, Load
from app.models.enums import LoadStatus
from app.repositories.clientes.clientes import ClienteRepository
from app.schemas.clientes.clientes import (
    ClienteCreate,
    ClienteResponse,
    ClienteUpdate,
    validate_document,
)

CLIENT_DATA_FIELDS = {
    "nombre",
    "documento",
    "tipo_documento",
    "tipo",
    "estado",
    "nombre_comercial",
    "telefono",
    "correo",
    "departamento",
    "ubicacion",
    "direccion",
    "contacto",
    "notas",
}


class ClienteService:
    def __init__(self, repository: ClienteRepository):
        self.repository = repository

    @staticmethod
    def _response(item: Client) -> ClienteResponse:
        data = {key: value for key, value in (item.data or {}).items() if key in CLIENT_DATA_FIELDS}
        data.update(
            id=item.id,
            nombre=item.name,
            documento=item.document,
            estado=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by,
        )
        return ClienteResponse.model_validate(data)

    def list(
        self, page: int, page_size: int, q: str | None, estado: str | None, tipo: str | None
    ) -> dict[str, Any]:
        total, items = self.repository.list(page, page_size, q, estado, tipo)
        return {
            "items": [self._response(item) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    def get(self, client_id: str) -> ClienteResponse:
        item = self.repository.get(client_id)
        if item is None:
            raise ApiError(404, "CLIENT_NOT_FOUND", "Cliente no encontrado")
        return self._response(item)

    def _raise_document_conflict(self, document: str, current_id: str | None = None) -> None:
        existing = self.repository.get_by_document(document)
        if existing is None or existing.id == current_id:
            return
        if existing.deleted_at is not None:
            raise ApiError(
                409,
                "CLIENT_DOCUMENT_ARCHIVED",
                "El documento pertenece a un cliente dado de baja. Reactiva ese cliente para volver a usarlo.",
                {"field": "documento", "client_id": existing.id},
            )
        raise ApiError(
            409,
            "CLIENT_DOCUMENT_DUPLICATE",
            "Ya existe un cliente registrado con este documento.",
            {"field": "documento", "client_id": existing.id},
        )

    def _integrity_conflict(self, document: str, current_id: str | None = None) -> None:
        try:
            self._raise_document_conflict(document, current_id)
        except ApiError:
            raise
        raise ApiError(
            409,
            "CLIENT_CONFLICT",
            "No se pudo guardar el cliente porque existe un conflicto con sus datos.",
            {"field": "documento"},
        )

    def create(self, payload: ClienteCreate, created_by: str) -> ClienteResponse:
        self._raise_document_conflict(payload.documento)
        data = payload.model_dump(mode="json")
        values = {
            "name": data["nombre"],
            "document": data["documento"],
            "status": data["estado"],
            "data": data,
            "created_by": created_by,
        }
        try:
            return self._response(self.repository.create(values))
        except IntegrityError:
            self._integrity_conflict(payload.documento)

    def update(self, client_id: str, payload: ClienteUpdate) -> ClienteResponse:
        item = self.repository.get(client_id)
        if item is None:
            raise ApiError(404, "CLIENT_NOT_FOUND", "Cliente no encontrado")
        changes = payload.model_dump(mode="json", exclude_unset=True)
        current = {
            key: value for key, value in (item.data or {}).items() if key in CLIENT_DATA_FIELDS
        }
        current.setdefault("nombre", item.name)
        current.setdefault("documento", item.document)
        current.setdefault("estado", item.status)
        merged = {**current, **changes}
        document = merged.get("documento")
        document_type = merged.get("tipo_documento")
        if document and document_type:
            validate_document(document_type, document)
        if document:
            self._raise_document_conflict(document, current_id=client_id)
        values: dict[str, Any] = {"data": merged}
        if "nombre" in changes:
            values["name"] = changes["nombre"]
        if "documento" in changes:
            values["document"] = changes["documento"]
        if "estado" in changes:
            values["status"] = changes["estado"]
        try:
            return self._response(self.repository.update(item, values))
        except IntegrityError:
            self._integrity_conflict(document or "", current_id=client_id)

    def delete(self, client_id: str) -> None:
        item = self.repository.get(client_id)
        if item is None:
            raise ApiError(404, "CLIENT_NOT_FOUND", "Cliente no encontrado")
        active_load = self.repository.db.scalar(
            select(Load.id)
            .where(
                Load.client_id == client_id,
                Load.deleted_at.is_(None),
                Load.status.not_in((LoadStatus.DELIVERED, LoadStatus.CANCELED)),
            )
            .limit(1)
        )
        if active_load:
            raise ApiError(
                409,
                "CLIENT_HAS_ACTIVE_LOADS",
                "No se puede dar de baja el cliente mientras tenga cargas sin entregar ni cancelar.",
                {"carga_id": active_load},
            )
        self.repository.delete(item)

    def reactivate(self, client_id: str) -> ClienteResponse:
        item = self.repository.get_including_archived(client_id)
        if item is None:
            raise ApiError(404, "CLIENT_NOT_FOUND", "Cliente no encontrado")
        if item.deleted_at is None:
            raise ApiError(409, "CLIENT_NOT_ARCHIVED", "El cliente no está dado de baja.")
        existing = self.repository.get_by_document(item.document or "")
        if existing is not None and existing.id != item.id and existing.deleted_at is None:
            raise ApiError(
                409,
                "CLIENT_DOCUMENT_DUPLICATE",
                "No se puede reactivar: el documento está en uso por otro cliente activo.",
                {"field": "documento", "client_id": existing.id},
            )
        try:
            return self._response(self.repository.reactivate(item))
        except IntegrityError:
            existing = self.repository.get_by_document(item.document or "")
            if existing is not None and existing.id != item.id and existing.deleted_at is None:
                raise ApiError(
                    409,
                    "CLIENT_DOCUMENT_DUPLICATE",
                    "No se puede reactivar: el documento está en uso por otro cliente activo.",
                    {"field": "documento", "client_id": existing.id},
                )
            raise ApiError(
                409,
                "CLIENT_CONFLICT",
                "No se pudo reactivar el cliente debido a un conflicto de integridad.",
            )
