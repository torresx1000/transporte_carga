from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class ReturnAllocation(AuditMixin, Base):
    __tablename__ = "retorno_desgloses"
    return_id: Mapped[str] = mapped_column(ForeignKey("retornos.id"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clientes.id"), index=True)
    returned_total: Mapped[int] = mapped_column(Integer, default=0)
    balance_period_id: Mapped[str | None] = mapped_column(
        ForeignKey("retorno_historial_cortes.id"), nullable=True, index=True
    )
