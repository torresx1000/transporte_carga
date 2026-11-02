from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class ReturnRecord(AuditMixin, Base):
    __tablename__ = "retornos"
    client_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    load_id: Mapped[str | None] = mapped_column(ForeignKey("cargas.id"), nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("viajes.id"), nullable=True, index=True)
    returned_total: Mapped[int] = mapped_column(Integer, default=0)
    balance_period_id: Mapped[str | None] = mapped_column(
        ForeignKey("retorno_historial_cortes.id"), nullable=True, index=True
    )


class ReturnBalanceCut(Base):
    __tablename__ = "retorno_historial_cortes"
    __table_args__ = (
        UniqueConstraint("client_id", "sequence", name="uq_retorno_historial_cliente_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    client_name: Mapped[str] = mapped_column(String(255))
    dispatched_total: Mapped[int] = mapped_column(Integer)
    returned_total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_email: Mapped[str] = mapped_column(String(255))
