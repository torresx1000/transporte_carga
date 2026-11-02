from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Expense(AuditMixin, Base):
    __tablename__ = "gastos"
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("viajes.id"), nullable=True, index=True)
    vehicle_id: Mapped[str | None] = mapped_column(
        ForeignKey("vehiculos.id"), nullable=True, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(80), index=True)
