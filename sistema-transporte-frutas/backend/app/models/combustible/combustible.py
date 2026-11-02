from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Fueling(AuditMixin, Base):
    __tablename__ = "combustible"
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("viajes.id"), nullable=True, index=True)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehiculos.id"), index=True)
    liters_milli: Mapped[int] = mapped_column(Integer, default=0)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    odometer: Mapped[int] = mapped_column(Integer, default=0)
