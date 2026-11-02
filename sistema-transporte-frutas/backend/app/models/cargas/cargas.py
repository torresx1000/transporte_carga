from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin, enum_values
from app.models.enums import LoadStatus, Priority

if TYPE_CHECKING:
    from app.models.viajes.viajes import Trip


class Load(AuditMixin, Base):
    __tablename__ = "cargas"
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clientes.id"), nullable=True, index=True
    )
    balance_period_id: Mapped[str | None] = mapped_column(
        ForeignKey("retorno_historial_cortes.id"), nullable=True, index=True
    )
    status: Mapped[LoadStatus] = mapped_column(
        Enum(LoadStatus, native_enum=False, values_callable=enum_values),
        default=LoadStatus.PENDING,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, values_callable=enum_values), default=Priority.NORMAL
    )
    jabas_dispatched: Mapped[int] = mapped_column(Integer, default=0)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("viajes.id"), nullable=True, index=True)
    product: Mapped[str] = mapped_column(String(100))
    variety: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit: Mapped[str] = mapped_column(String(30), default="kg")
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    pickup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    charge_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", server_default="PEN")

    trip: Mapped["Trip | None"] = relationship("Trip", back_populates="loads")
    origen_id: Mapped[int | None] = mapped_column(
        ForeignKey("ciudades.id_ciudad"), nullable=True, index=True
    )
    destino_id: Mapped[int | None] = mapped_column(
        ForeignKey("ciudades.id_ciudad"), nullable=True, index=True
    )
    stages: Mapped[list["LoadStage"]] = relationship(
        order_by="LoadStage.orden", cascade="all, delete-orphan"
    )


class LoadStage(AuditMixin, Base):
    __tablename__ = "detalle_carga_viajes"
    __table_args__ = (
        UniqueConstraint("id_carga", "orden", name="uq_carga_etapa_orden"),
        UniqueConstraint("id_carga", "id_viaje", name="uq_carga_etapa_viaje"),
        CheckConstraint(
            "estado IN ('pendiente', 'en_transito', 'completado', 'cancelado')",
            name="ck_etapa_estado",
        ),
        CheckConstraint("orden > 0", name="ck_etapa_orden"),
        CheckConstraint("origen_id <> destino_id", name="ck_etapa_extremos"),
    )
    id_carga: Mapped[str] = mapped_column(ForeignKey("cargas.id"), index=True)
    id_viaje: Mapped[str] = mapped_column(ForeignKey("viajes.id"), index=True)
    orden: Mapped[int] = mapped_column(Integer)
    origen_id: Mapped[int] = mapped_column(ForeignKey("ciudades.id_ciudad"))
    destino_id: Mapped[int] = mapped_column(ForeignKey("ciudades.id_ciudad"))
    estado: Mapped[str] = mapped_column(String(30), default="pendiente", server_default="pendiente")
    salida_real: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    llegada_real: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
