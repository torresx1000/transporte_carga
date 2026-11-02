from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin, enum_values
from app.models.enums import UserRole


class User(AuditMixin, Base):
    __tablename__ = "usuarios"
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, values_callable=enum_values),
        default=UserRole.OPERATOR,
        index=True,
    )
    active: Mapped[bool] = mapped_column(default=True)
