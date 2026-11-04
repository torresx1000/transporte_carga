from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin, enum_values
from app.models.enums import UserRole
from app.models.roles import AccessRole


class User(AuditMixin, Base):
    __tablename__ = "usuarios"
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, values_callable=enum_values),
        default=UserRole.OPERATOR,
        index=True,
    )
    permission_role_id: Mapped[str | None] = mapped_column(
        ForeignKey("roles_acceso.id"), nullable=True, index=True
    )
    permission_role: Mapped[AccessRole | None] = relationship(back_populates="users")
    active: Mapped[bool] = mapped_column(default=True)
