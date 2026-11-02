from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Client(AuditMixin, Base):
    __tablename__ = "clientes"
    name: Mapped[str] = mapped_column(String(255), index=True)
    document: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="activo", index=True)
