from fastapi import HTTPException

from app.models.entities import Document, Load, Payment, Trip, User
from app.repositories.portal import PortalRepository


class PortalService:
    def __init__(self, repository: PortalRepository):
        self.repository = repository

    @staticmethod
    def _load(item: Load) -> dict:
        return {
            "id": item.id,
            "codigo": item.code,
            "estado": item.status,
            "producto": item.product,
            "procedencia": item.origin,
            "destino": item.destination,
            "etapas": [
                {
                    "orden": r.orden,
                    "estado": r.estado,
                    "origen_id": r.origen_id,
                    "destino_id": r.destino_id,
                    "salida_real": r.salida_real,
                    "llegada_real": r.llegada_real,
                }
                for r in item.stages
            ],
        }

    @staticmethod
    def _trip(item: Trip) -> dict:
        route = item.route
        return {
            "id": item.id,
            "codigo": item.code,
            "estado": item.status,
            "fecha_salida_programada": item.scheduled_start_at,
            "fecha_entrega_estimada": item.scheduled_end_at,
            "salida_real": item.actual_start_at,
            "entrega_real": item.actual_end_at,
            "ruta": (
                {"nombre": route.name, "origen": route.origin, "destino": route.destination}
                if route is not None
                else None
            ),
        }

    @staticmethod
    def _document(item: Document) -> dict:
        return {
            **item.data,
            "id": item.id,
            "tipo": item.document_type,
            "vence_en": item.expires_at,
        }

    @staticmethod
    def _payment(item: Payment) -> dict:
        return {
            **item.data,
            "id": item.id,
            "monto_centimos": item.amount,
            "estado": item.status,
        }

    def _required(self, item, resource: str):
        if item is None:
            raise HTTPException(404, f"{resource} no encontrado")
        return item

    def loads(self, user: User) -> list[dict]:
        return [self._load(item) for item in self.repository.loads(user)]

    def load(self, user: User, load_id: str) -> dict:
        return self._load(self._required(self.repository.load(user, load_id), "Carga"))

    def trips(self, user: User) -> list[dict]:
        return [self._trip(item) for item in self.repository.trips(user)]

    def trip(self, user: User, trip_id: str) -> dict:
        return self._trip(self._required(self.repository.trip(user, trip_id), "Viaje"))

    def documents(self, user: User) -> list[dict]:
        return [self._document(item) for item in self.repository.documents(user)]

    def document(self, user: User, document_id: str) -> dict:
        return self._document(
            self._required(self.repository.document(user, document_id), "Documento")
        )

    def payments(self, user: User) -> list[dict]:
        return [self._payment(item) for item in self.repository.payments(user)]

    def payment(self, user: User, payment_id: str) -> dict:
        return self._payment(self._required(self.repository.payment(user, payment_id), "Pago"))
