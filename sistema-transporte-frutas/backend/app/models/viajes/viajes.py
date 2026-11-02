from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin, enum_values
from app.models.enums import TripStatus

if TYPE_CHECKING:
    from app.models.cargas.cargas import Load
    from app.models.rutas.rutas import Route


class Trip(AuditMixin, Base):
    __tablename__ = "viajes"
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    vehicle_id: Mapped[str | None] = mapped_column(
        ForeignKey("vehiculos.id"), nullable=True, index=True
    )
    driver_id: Mapped[str | None] = mapped_column(
        ForeignKey("conductores.id"), nullable=True, index=True
    )
    route_id: Mapped[str | None] = mapped_column(ForeignKey("rutas.id"), nullable=True, index=True)
    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, native_enum=False, values_callable=enum_values),
        default=TripStatus.SCHEDULED,
        index=True,
    )
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    freight_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", server_default="PEN")

    loads: Mapped[list["Load"]] = relationship("Load", back_populates="trip")
    route: Mapped["Route | None"] = relationship("Route")
