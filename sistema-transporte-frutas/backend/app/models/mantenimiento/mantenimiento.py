from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Maintenance(AuditMixin, Base):
    __tablename__ = "mantenimiento"
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehiculos.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="programado", index=True)
