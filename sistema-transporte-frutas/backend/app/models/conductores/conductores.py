from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Driver(AuditMixin, Base):
    __tablename__ = "conductores"
    name: Mapped[str] = mapped_column(String(255), index=True)
    document: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    license_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    license_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    medical_exam_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="disponible", index=True)
