from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cargas.cargas import LoadStage
from app.models.entities import Document, Load, Payment, Trip, User


class PortalRepository:
    """Queries constrained to the client linked to the authenticated user."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _client_id(user: User) -> str | None:
        return user.data.get("client_id") if user.data else None

    def loads(self, user: User) -> list[Load]:
        client_id = self._client_id(user)
        if not client_id:
            return []
        query = select(Load).where(
            Load.client_id == client_id,
            Load.client_id.is_not(None),
            Load.deleted_at.is_(None),
        )
        return list(self.db.scalars(query).all())

    def load(self, user: User, load_id: str) -> Load | None:
        client_id = self._client_id(user)
        if not client_id:
            return None
        query = select(Load).where(
            Load.id == load_id,
            Load.client_id == client_id,
            Load.client_id.is_not(None),
            Load.deleted_at.is_(None),
        )
        return self.db.scalar(query)

    def trips(self, user: User) -> list[Trip]:
        client_id = self._client_id(user)
        if not client_id:
            return []
        query = (
            select(Trip)
            .join(LoadStage, LoadStage.id_viaje == Trip.id)
            .join(Load, LoadStage.id_carga == Load.id)
            .options(joinedload(Trip.route))
            .where(
                Load.client_id == client_id,
                Load.client_id.is_not(None),
                Load.deleted_at.is_(None),
                Trip.deleted_at.is_(None),
            )
            .distinct()
        )
        return list(self.db.scalars(query).all())

    def trip(self, user: User, trip_id: str) -> Trip | None:
        client_id = self._client_id(user)
        if not client_id:
            return None
        query = (
            select(Trip)
            .join(LoadStage, LoadStage.id_viaje == Trip.id)
            .join(Load, LoadStage.id_carga == Load.id)
            .options(joinedload(Trip.route))
            .where(
                Load.client_id == client_id,
                Load.client_id.is_not(None),
                Load.deleted_at.is_(None),
                Trip.deleted_at.is_(None),
                Trip.id == trip_id,
            )
        )
        return self.db.scalar(query)

    def documents(self, user: User) -> list[Document]:
        client_id = self._client_id(user)
        if not client_id:
            return []
        query = select(Document).where(
            Document.owner_type == "cliente",
            Document.owner_id == client_id,
            Document.deleted_at.is_(None),
        )
        return list(self.db.scalars(query).all())

    def document(self, user: User, document_id: str) -> Document | None:
        client_id = self._client_id(user)
        if not client_id:
            return None
        query = select(Document).where(
            Document.id == document_id,
            Document.owner_type == "cliente",
            Document.owner_id == client_id,
            Document.deleted_at.is_(None),
        )
        return self.db.scalar(query)

    def payments(self, user: User) -> list[Payment]:
        client_id = self._client_id(user)
        if not client_id:
            return []
        query = select(Payment).where(
            Payment.client_id == client_id,
            Payment.client_id.is_not(None),
            Payment.deleted_at.is_(None),
        )
        return list(self.db.scalars(query).all())

    def payment(self, user: User, payment_id: str) -> Payment | None:
        client_id = self._client_id(user)
        if not client_id:
            return None
        query = select(Payment).where(
            Payment.id == payment_id,
            Payment.client_id == client_id,
            Payment.client_id.is_not(None),
            Payment.deleted_at.is_(None),
        )
        return self.db.scalar(query)
