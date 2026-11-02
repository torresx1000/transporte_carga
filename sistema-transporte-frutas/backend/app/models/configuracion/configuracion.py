from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class Setting(AuditMixin, Base):
    __tablename__ = "configuracion"
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
