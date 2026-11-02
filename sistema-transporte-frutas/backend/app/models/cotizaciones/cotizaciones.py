from datetime import date

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin, enum_values
from app.models.enums import QuotationStatus


class Quotation(AuditMixin, Base):
    __tablename__ = "cotizaciones"
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clientes.id"), nullable=True, index=True
    )
    route_id: Mapped[str | None] = mapped_column(ForeignKey("rutas.id"), nullable=True, index=True)
    status: Mapped[QuotationStatus] = mapped_column(
        Enum(QuotationStatus, native_enum=False, values_callable=enum_values),
        default=QuotationStatus.DRAFT,
        index=True,
    )
    issue_date: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", server_default="PEN")
    discount_rate_bps: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    discount_minor: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    tax_rate_bps: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    subtotal: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    tax: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    total: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
