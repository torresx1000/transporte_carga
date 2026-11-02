from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.entities import Driver, Load, Route, Trip, Vehicle
from app.models.cargas.cargas import LoadStage
from app.services.etapas.etapas import EtapasService, utc
from app.schemas.cargas.cargas import EtapaInput
from app.models.enums import LoadStatus, TripStatus
from app.repositories.records import RecordRepository
from app.schemas.viajes.viajes import (
    ViajeCreate,
    ViajeResponse,
    ViajeUpdate,
)


ACTIVE_TRIP_STATES = (TripStatus.SCHEDULED, TripStatus.IN_PROGRESS, TripStatus.INCIDENT)
TERMINAL_LOAD_STATES = (LoadStatus.DELIVERED, LoadStatus.CANCELED)
LIMA_TZ = ZoneInfo("America/Lima")


class ViajeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RecordRepository(db, Trip)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _lock_vehicle_driver(self, vehicle_id: str, driver_id: str):
        vehicle = self.db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id).with_for_update())
        driver = self.db.scalar(select(Driver).where(Driver.id == driver_id).with_for_update())
        if vehicle is None or vehicle.deleted_at is not None:
            raise ApiError(
                409,
                "TRIP_VEHICLE_INACTIVE",
                "El vehículo no existe o está dado de baja.",
                {"field": "vehiculo_id"},
            )
        if vehicle.status not in {"disponible", "en_viaje"}:
            raise ApiError(
                409,
                "TRIP_VEHICLE_INACTIVE",
                "El vehículo no está disponible para asignación.",
                {"field": "vehiculo_id"},
            )
        if driver is None or driver.deleted_at is not None:
            raise ApiError(
                409,
                "TRIP_DRIVER_INACTIVE",
                "El conductor no existe o está dado de baja.",
                {"field": "conductor_id"},
            )
        if driver.status not in {"disponible", "en_viaje"}:
            raise ApiError(
                409,
                "TRIP_DRIVER_INACTIVE",
                "El conductor no está disponible para asignación.",
                {"field": "conductor_id"},
            )
        return vehicle, driver

    def _require_active_route(self, route_id: str) -> Route:
        route = self.db.get(Route, route_id)
        if (
            route is None
            or route.deleted_at is not None
            or route.status not in {"activa", "active", "activo"}
        ):
            raise ApiError(
                409,
                "TRIP_ROUTE_INACTIVE",
                "La ruta no existe o está inactiva.",
                {"field": "ruta_id"},
            )
        return route

    def _check_overlaps(
        self,
        vehicle_id: str,
        driver_id: str,
        start: datetime,
        end: datetime,
        exclude_id: str | None = None,
    ) -> None:
        query = select(Trip).where(
            Trip.deleted_at.is_(None),
            Trip.status.in_(ACTIVE_TRIP_STATES),
            Trip.scheduled_start_at < end,
            Trip.scheduled_end_at > start,
        )
        if exclude_id:
            query = query.where(Trip.id != exclude_id)
        conflicts = self.db.scalars(query.with_for_update()).all()
        if any(item.vehicle_id == vehicle_id for item in conflicts):
            raise ApiError(
                409,
                "TRIP_VEHICLE_OVERLAP",
                "El vehículo ya tiene un viaje activo en ese horario.",
                {"field": "vehiculo_id"},
            )
        if any(item.driver_id == driver_id for item in conflicts):
            raise ApiError(
                409,
                "TRIP_DRIVER_OVERLAP",
                "El conductor ya tiene un viaje activo en ese horario.",
                {"field": "conductor_id"},
            )

    @staticmethod
    def _load_weight(load: Load) -> tuple[Decimal | None, bool]:
        if load.gross_weight_kg is not None:
            return Decimal(load.gross_weight_kg), False
        if load.net_weight_kg is not None:
            return Decimal(load.net_weight_kg), True
        return None, True

    def ensure_capacity(self, trip, actor_role=None):
        return EtapasService(self.db).capacity(trip)

    def _payload(self, item: Trip) -> ViajeResponse:
        loads = self.db.scalars(
            select(Load)
            .join(LoadStage, LoadStage.id_carga == Load.id)
            .where(LoadStage.id_viaje == item.id, Load.deleted_at.is_(None))
            .order_by(Load.created_at, Load.id)
        ).all()
        vehicle = self.db.get(Vehicle, item.vehicle_id) if item.vehicle_id else None
        weights = [self._load_weight(load) for load in loads]
        known_weights = [weight for weight, _ in weights if weight is not None]
        total = sum(known_weights, Decimal("0")) if known_weights else None
        total, incomplete = EtapasService(self.db).capacity(item)
        return ViajeResponse.model_validate(
            {
                "id": item.id,
                "codigo": item.code,
                "vehiculo_id": item.vehicle_id,
                "conductor_id": item.driver_id,
                "ruta_id": item.route_id,
                "estado": item.status,
                "fecha_salida_programada": item.scheduled_start_at,
                "fecha_entrega_estimada": item.scheduled_end_at,
                "salida_real": item.actual_start_at,
                "entrega_real": item.actual_end_at,
                "flete_centimos": item.freight_amount_minor,
                "moneda": item.currency,
                "etapas": [
                    EtapasService(self.db).serialize(row)
                    for row in EtapasService(self.db).stages(trip_id=item.id)
                ],
                "cargas_ids": [load.id for load in loads],
                "peso_total_kg": total,
                "capacidad_kg": vehicle.capacity_kg if vehicle else None,
                "peso_incompleto": incomplete,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "created_by": item.created_by,
            }
        )

    def list(self, page: int, page_size: int, q: str | None, **filters):
        mappings = {
            "estado": "status",
            "ruta_id": "route_id",
            "vehiculo_id": "vehicle_id",
            "conductor_id": "driver_id",
        }
        mapped = {
            key: (column, filters.get(key))
            for key, column in mappings.items()
            if filters.get(key) not in (None, "")
        }
        total, rows = self.repo.list_configured(page, page_size, q, ("code", "status"), mapped)
        return {
            "items": [self._payload(item) for item in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    def get(self, trip_id: str) -> ViajeResponse:
        item = self.repo.get(trip_id)
        if item is None:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viaje no encontrado.")
        return self._payload(item)

    def create(self, payload: ViajeCreate, created_by: str) -> ViajeResponse:
        vehicle, driver = self._lock_vehicle_driver(payload.vehiculo_id, payload.conductor_id)
        self._require_active_route(payload.ruta_id)
        self._check_overlaps(
            payload.vehiculo_id,
            payload.conductor_id,
            payload.fecha_salida_programada,
            payload.fecha_entrega_estimada,
        )
        departure_date = payload.fecha_salida_programada.astimezone(LIMA_TZ).date()
        day_start = datetime.combine(
            departure_date, time.min, tzinfo=LIMA_TZ
        ).astimezone(timezone.utc)
        day_end = datetime.combine(
            departure_date + timedelta(days=1), time.min, tzinfo=LIMA_TZ
        ).astimezone(timezone.utc)
        # Count every trip scheduled on the Lima calendar date, including cancelled or
        # archived trips, so a previously used sequence number is never reused.
        daily_trip_count = self.db.scalar(
            select(func.count(Trip.id)).where(
                Trip.scheduled_start_at >= day_start,
                Trip.scheduled_start_at < day_end,
            )
        ) or 0
        code = f"VJ-{departure_date:%d_%m_%Y}-{daily_trip_count + 1}"
        item = Trip(
            code=code,
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            route_id=payload.ruta_id,
            status=TripStatus.SCHEDULED,
            scheduled_start_at=payload.fecha_salida_programada,
            scheduled_end_at=payload.fecha_entrega_estimada,
            freight_amount_minor=payload.flete_centimos,
            currency="PEN",
            created_by=created_by,
            data={},
        )
        self.db.add(item)
        try:
            self.db.flush()
            for load_id in payload.cargas_ids:
                load = self.db.get(Load, load_id)
                if not load:
                    raise ApiError(422, "LOAD_NOT_FOUND", "Carga no encontrada")
                rows = EtapasService(self.db).stages(load_id=load_id)
                requested = [
                    EtapaInput(viaje_id=r.id_viaje, origen_id=r.origen_id, destino_id=r.destino_id)
                    for r in rows
                ]
                requested.append(
                    EtapaInput(
                        viaje_id=item.id,
                        origen_id=rows[-1].destino_id if rows else load.origen_id,
                        destino_id=load.destino_id,
                    )
                )
                EtapasService(self.db).plan(load_id, requested, created_by, commit=False)
            self.ensure_capacity(item)
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise ApiError(
                409,
                "TRIP_CONFLICT",
                "No se pudo programar el viaje por un conflicto con código o asignación.",
            ) from None
        except Exception:
            self.db.rollback()
            raise
        return self._payload(item)

    def update(self, trip_id: str, payload: ViajeUpdate, user_id: str, role: str) -> ViajeResponse:
        item = self.db.scalar(
            select(Trip).where(Trip.id == trip_id, Trip.deleted_at.is_(None)).with_for_update()
        )
        if item is None:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viaje no encontrado.")
        if item.status != TripStatus.SCHEDULED:
            raise ApiError(
                409,
                "TRIP_IMMUTABLE",
                "Solo se puede editar la programación de un viaje programado.",
            )
        changes = payload.model_dump(exclude_unset=True)
        mapping = {
            "codigo": "code",
            "vehiculo_id": "vehicle_id",
            "conductor_id": "driver_id",
            "ruta_id": "route_id",
            "fecha_salida_programada": "scheduled_start_at",
            "fecha_entrega_estimada": "scheduled_end_at",
            "flete_centimos": "freight_amount_minor",
            "moneda": "currency",
        }
        merged = {key: getattr(item, column) for key, column in mapping.items()}
        merged.update(changes)
        start, end = merged["fecha_salida_programada"], merged["fecha_entrega_estimada"]
        if start is None or end is None or utc(end) <= utc(start):
            raise ApiError(
                422,
                "TRIP_INVALID_SCHEDULE",
                "La fecha estimada de entrega debe ser posterior a la salida.",
                {"field": "fecha_entrega_estimada"},
            )
        vehicle, driver = self._lock_vehicle_driver(merged["vehiculo_id"], merged["conductor_id"])
        self._require_active_route(merged["ruta_id"])
        self._check_overlaps(vehicle.id, driver.id, start, end, exclude_id=item.id)
        for request_field, model_field in mapping.items():
            if request_field in changes:
                setattr(item, model_field, changes[request_field])
        try:
            self.db.flush()
            self.ensure_capacity(item)
            EtapasService(self.db).validate_trip_schedule(item)
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise ApiError(
                409, "TRIP_CONFLICT", "No se pudo actualizar el viaje por un conflicto de datos."
            ) from None
        except Exception:
            self.db.rollback()
            raise
        return self._payload(item)

    def set_loads(self, trip_id, payload, user_id, role):
        trip = self.db.scalar(
            select(Trip).where(Trip.id == trip_id, Trip.deleted_at.is_(None)).with_for_update()
        )
        if not trip or trip.status != TripStatus.SCHEDULED:
            raise ApiError(409, "TRIP_IMMUTABLE", "Asigna cargas solo a viajes programados")
        service = EtapasService(self.db)
        old = service.stages(trip_id=trip_id)
        old_ids = {r.id_carga for r in old}
        try:
            for load_id in sorted(old_ids | set(payload.cargas_ids)):
                rows = service.stages(load_id=load_id)
                requested = [
                    EtapaInput(viaje_id=r.id_viaje, origen_id=r.origen_id, destino_id=r.destino_id)
                    for r in rows
                ]
                if load_id not in payload.cargas_ids:
                    if rows[-1].id_viaje != trip_id:
                        raise ApiError(
                            409,
                            "STAGE_CHAIN",
                            "Modifica el plan completo desde el detalle de la carga",
                        )
                    requested = requested[:-1]
                elif load_id not in old_ids:
                    load = self.db.get(Load, load_id)
                    if not load:
                        raise ApiError(422, "LOAD_NOT_FOUND", "Carga no encontrada")
                    requested.append(
                        EtapaInput(
                            viaje_id=trip_id,
                            origen_id=rows[-1].destino_id if rows else load.origen_id,
                            destino_id=load.destino_id,
                        )
                    )
                service.plan(load_id, requested, user_id, commit=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._payload(trip)

    def transition(self, trip_id, payload):
        trip = self.db.scalar(
            select(Trip).where(Trip.id == trip_id, Trip.deleted_at.is_(None)).with_for_update()
        )
        if not trip:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viaje no encontrado")
        target = payload.estado
        allowed = {
            TripStatus.SCHEDULED: {TripStatus.IN_PROGRESS, TripStatus.CANCELED},
            TripStatus.IN_PROGRESS: {TripStatus.INCIDENT, TripStatus.COMPLETED},
            TripStatus.INCIDENT: {TripStatus.IN_PROGRESS, TripStatus.COMPLETED},
        }
        if target not in allowed.get(trip.status, set()):
            raise ApiError(409, "TRIP_TRANSITION", "Transición del viaje no permitida")
        service = EtapasService(self.db)
        rows = service.stages(trip_id=trip_id)
        try:
            if target == TripStatus.IN_PROGRESS and trip.status == TripStatus.SCHEDULED:
                if not rows:
                    raise ApiError(
                        409, "TRIP_WITHOUT_LOADS", "Asigna cargas antes de iniciar el viaje"
                    )
                service.capacity(trip)
                trip.actual_start_at = self._now()
                route = self._require_active_route(trip.route_id)
                for row in rows:
                    if row.origen_id == route.origen_id:
                        previous = [
                            r for r in service.stages(load_id=row.id_carga) if r.orden < row.orden
                        ]
                        if any(r.estado != "completado" for r in previous):
                            raise ApiError(
                                409,
                                "PREVIOUS_STAGE_PENDING",
                                "Completa el tramo anterior de cada carga antes de iniciar",
                            )
                        row.estado = "en_transito"
                        row.salida_real = trip.actual_start_at
            elif target == TripStatus.COMPLETED:
                if any(r.estado != "completado" for r in rows):
                    raise ApiError(
                        409,
                        "TRIP_STAGES_PENDING",
                        "Completa todas las etapas de este viaje antes de cerrarlo",
                    )
                trip.actual_end_at = self._now()
            elif target == TripStatus.CANCELED:
                for row in rows:
                    chain = service.stages(load_id=row.id_carga)
                    requested = [
                        EtapaInput(
                            viaje_id=r.id_viaje, origen_id=r.origen_id, destino_id=r.destino_id
                        )
                        for r in chain
                        if r.orden < row.orden
                    ]
                    service.plan(row.id_carga, requested, trip.created_by, commit=False)
            trip.status = target
            self.db.flush()
            for load_id in {r.id_carga for r in rows}:
                service.sync(self.db.get(Load, load_id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._payload(trip)

    def delete(self, trip_id: str) -> None:
        trip = self.repo.get(trip_id)
        if trip is None:
            raise ApiError(404, "TRIP_NOT_FOUND", "Viaje no encontrado.")
        if trip.status in ACTIVE_TRIP_STATES:
            raise ApiError(
                409,
                "TRIP_ACTIVE",
                "No se puede dar de baja un viaje programado, en curso o con incidencia.",
            )
        self.repo.delete(trip)


def guard_reference_deactivation(db: Session, module: str, record_id: str) -> None:
    foreign_key = {
        "conductores": Trip.driver_id,
        "vehiculos": Trip.vehicle_id,
        "rutas": Trip.route_id,
    }.get(module)
    if foreign_key is None:
        return
    active_trip = db.scalar(
        select(Trip.id)
        .where(
            foreign_key == record_id,
            Trip.deleted_at.is_(None),
            Trip.status.in_(ACTIVE_TRIP_STATES),
        )
        .limit(1)
    )
    if active_trip:
        raise ApiError(
            409,
            "REFERENCE_HAS_ACTIVE_TRIPS",
            "No se puede dar de baja el recurso mientras tenga viajes programados, en curso o con incidencia.",
            {"viaje_id": active_trip},
        )
