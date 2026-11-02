from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class QuotationItem(AuditMixin, Base):
    __tablename__ = "cotizacion_items"
    __table_args__ = (
        UniqueConstraint("quotation_id", "line_order", name="uq_cotizacion_items_order"),
    )
    quotation_id: Mapped[str] = mapped_column(ForeignKey("cotizaciones.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price_cents: Mapped[int] = mapped_column(BigInteger)
    line_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
