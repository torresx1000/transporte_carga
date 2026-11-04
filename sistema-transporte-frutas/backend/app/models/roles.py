from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin

if TYPE_CHECKING:
    from app.models.usuarios.usuarios import User


class AccessRole(AuditMixin, Base):
    __tablename__ = "roles_acceso"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="permission_role")


class AccessRoleAudit(AuditMixin, Base):
    __tablename__ = "roles_acceso_auditoria"

    role_id: Mapped[str | None] = mapped_column(
        ForeignKey("roles_acceso.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
