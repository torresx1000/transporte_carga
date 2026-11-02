from datetime import datetime, timezone
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.models.base import AuditMixin


class RecordRepository:
    def __init__(self, db: Session, model: type[AuditMixin]):
        self.db, self.model = db, model

    def list(self, page: int, page_size: int, filters: dict):
        query = select(self.model).where(self.model.deleted_at.is_(None))
        for name, value in filters.items():
            if name == "_search":
                columns = [
                    getattr(self.model, field)
                    for field in ("name", "code", "plate", "origin", "destination", "document")
                    if hasattr(self.model, field)
                ]
                query = (
                    query.where(or_(*(column.ilike(f"%{value}%") for column in columns)))
                    if columns
                    else query
                )
            elif value is not None and hasattr(self.model, name):
                query = query.where(getattr(self.model, name) == value)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(
            query.order_by(self.model.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return total, items

    def list_configured(
        self,
        page: int,
        page_size: int,
        q: str | None,
        search_fields: tuple[str, ...],
        filters: dict[str, tuple[str, object]],
    ):
        """List with schema-factory search/filter mappings; legacy list stays unchanged."""
        query = select(self.model).where(self.model.deleted_at.is_(None))
        if q:
            expressions = [self._field_expression(field) for field in search_fields]
            expressions = [expression for expression in expressions if expression is not None]
            if expressions:
                query = query.where(
                    or_(*(expression.ilike(f"%{q.strip()}%") for expression in expressions))
                )
        for _query_name, (field_path, value) in filters.items():
            if value is not None:
                expression = self._field_expression(field_path)
                if expression is not None:
                    query = query.where(expression == value)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(
            query.order_by(self.model.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return total, items

    def _field_expression(self, field_path: str):
        if field_path.startswith("data."):
            return self.model.data[field_path.removeprefix("data.")].as_string()
        if field_path == "client.name" and hasattr(self.model, "client_id"):
            from app.models.entities import Client

            return select(Client.name).where(Client.id == self.model.client_id).scalar_subquery()
        return getattr(self.model, field_path, None)

    def get(self, record_id: str):
        item = self.db.get(self.model, record_id)
        return item if item and item.deleted_at is None else None

    def get_including_archived(self, record_id: str):
        return self.db.get(self.model, record_id)

    def create(self, values: dict):
        item = self.model(**values)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item, values: dict):
        for key, value in values.items():
            setattr(item, key, value)
        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item):
        item.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    def reactivate(self, item):
        item.deleted_at = None
        item.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(item)
        return item
