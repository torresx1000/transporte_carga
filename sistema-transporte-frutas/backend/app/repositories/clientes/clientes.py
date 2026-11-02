from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import Client


class ClienteRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, page: int, page_size: int, q: str | None, estado: str | None, tipo: str | None):
        query = select(Client).where(Client.deleted_at.is_(None))
        if estado:
            query = query.where(Client.status == estado)
        if tipo:
            query = query.where(Client.data["tipo"].as_string() == tipo)
        if q:
            term = f"%{q.strip()}%"
            query = query.where(
                or_(
                    Client.name.ilike(term),
                    Client.document.ilike(term),
                    *(
                        Client.data[field].as_string().ilike(term)
                        for field in (
                            "nombre_comercial",
                            "telefono",
                            "correo",
                            "contacto",
                            "departamento",
                            "ubicacion",
                        )
                    ),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(
            query.order_by(Client.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return total, items

    def get(self, client_id: str) -> Client | None:
        item = self.db.get(Client, client_id)
        return item if item and item.deleted_at is None else None

    def get_including_archived(self, client_id: str) -> Client | None:
        return self.db.get(Client, client_id)

    def get_by_document(self, document: str) -> Client | None:
        return self.db.scalar(select(Client).where(func.upper(Client.document) == document.upper()))

    def create(self, values: dict) -> Client:
        item = Client(**values)
        self.db.add(item)
        try:
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise
        return item

    def update(self, item: Client, values: dict) -> Client:
        for key, value in values.items():
            setattr(item, key, value)
        item.updated_at = datetime.now(timezone.utc)
        try:
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise
        return item

    def delete(self, item: Client) -> None:
        item.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    def reactivate(self, item: Client) -> Client:
        item.deleted_at = None
        item.status = "activo"
        item.data = {**(item.data or {}), "estado": "activo"}
        item.updated_at = datetime.now(timezone.utc)
        try:
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise
        return item
