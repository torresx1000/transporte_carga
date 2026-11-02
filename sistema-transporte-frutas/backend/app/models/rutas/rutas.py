from sqlalchemy import (
    BigInteger,
    Integer,
    Numeric,
    String,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import AuditMixin


class Route(AuditMixin, Base):
    __tablename__ = "rutas"
    code: Mapped[str | None] = mapped_column(String(10), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    origin: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str] = mapped_column(String(255))
    origen_id: Mapped[int] = mapped_column(ForeignKey("ciudades.id_ciudad"), index=True)
    destino_id: Mapped[int] = mapped_column(ForeignKey("ciudades.id_ciudad"), index=True)
    stops: Mapped[list["RouteStop"]] = relationship(
        cascade="all, delete-orphan", order_by="RouteStop.orden"
    )
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tolls_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reference_tariff_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class City(Base):
    __tablename__ = "ciudades"
    id_ciudad: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    departamento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    distrito: Mapped[str | None] = mapped_column(String(100), nullable=True)


class RouteStop(Base):
    __tablename__ = "paradas"
    __table_args__ = (
        UniqueConstraint("id_ruta", "orden", name="uq_paradas_ruta_orden"),
        CheckConstraint("orden > 0", name="ck_paradas_orden"),
        CheckConstraint("tiempo_espera >= 0", name="ck_paradas_espera"),
    )
    id_parada: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_ruta: Mapped[str] = mapped_column(ForeignKey("rutas.id"), index=True)
    ciudad_id: Mapped[int] = mapped_column(ForeignKey("ciudades.id_ciudad"), index=True)
    orden: Mapped[int] = mapped_column(Integer)
    tiempo_espera: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
