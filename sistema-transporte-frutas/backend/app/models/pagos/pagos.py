from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Payment(AuditMixin, Base):
    __tablename__ = "pagos"
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clientes.id"), nullable=True, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="pendiente", index=True)
