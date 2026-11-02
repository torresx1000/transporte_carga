from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Vehicle(AuditMixin, Base):
    __tablename__ = "vehiculos"
    plate: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    vin: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    fleet_code: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    capacity_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_trailer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trailer_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="disponible", index=True)
