from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Document(AuditMixin, Base):
    __tablename__ = "documentos"
    owner_type: Mapped[str] = mapped_column(String(40), index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
