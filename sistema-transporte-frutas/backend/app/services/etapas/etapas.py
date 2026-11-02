from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, delete
from app.core.errors import ApiError
from app.models.cargas.cargas import Load, LoadStage
from app.models.entities import Trip, Vehicle, Client
from app.models.rutas.rutas import City, Route
from app.models.enums import LoadStatus, TripStatus


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


class EtapasService:
    def __init__(self, db):
        self.db = db

    def stages(self, load_id=None, trip_id=None):
        q = select(LoadStage)
        if load_id:
            q = q.where(LoadStage.id_carga == load_id)
        if trip_id:
            q = q.where(LoadStage.id_viaje == trip_id)
        return list(self.db.scalars(q.order_by(LoadStage.id_carga, LoadStage.orden)).all())

    def serialize(self, row):
        trip = self.db.get(Trip, row.id_viaje)
        origin = self.db.get(City, row.origen_id)
        destination = self.db.get(City, row.destino_id)
        return dict(
            id=row.id,
            carga_id=row.id_carga,
            viaje_id=row.id_viaje,
            viaje_codigo=trip.code,
            orden=row.orden,
            origen_id=row.origen_id,
            destino_id=row.destino_id,
            origen=origin.nombre,
            destino=destination.nombre,
            estado=row.estado,
            salida_real=row.salida_real,
            llegada_real=row.llegada_real,
            salida_programada=trip.scheduled_start_at,
            llegada_estimada=trip.scheduled_end_at,
        )

    def path(self, trip):
        route = self.db.get(Route, trip.route_id)
        if not route:
            raise ApiError(409, "ROUTE_INACTIVE", "El viaje necesita una ruta activa")
        return [route.origen_id, *[p.ciudad_id for p in route.stops], route.destino_id]

    def interval(self, trip, origin, destination):
        path = self.path(trip)
        pairs = [
            (i, j)
            for i, x in enumerate(path)
            for j, y in enumerate(path)
            if x == origin and y == destination and i < j
        ]
        if not pairs:
            raise ApiError(
                422,
                "STAGE_ROUTE_MISMATCH",
                "El tramo no pertenece al recorrido del viaje o estÃ¡ en sentido inverso",
            )
        return pairs[0]

    def validate_trip_schedule(self, trip):
        for row in self.stages(trip_id=trip.id):
            rows = self.stages(load_id=row.id_carga)
            for previous, current in zip(rows, rows[1:]):
                a = self.db.get(Trip, previous.id_viaje)
                b = self.db.get(Trip, current.id_viaje)
                if utc(a.scheduled_end_at) > utc(b.scheduled_start_at):
                    raise ApiError(
                        409,
                        "STAGE_SCHEDULE_OVERLAP",
                        "El horario rompe la secuencia de transporte de una carga",
                    )

    def capacity(self, trip):
        vehicle = self.db.get(Vehicle, trip.vehicle_id)
        if not vehicle or not vehicle.capacity_kg:
            raise ApiError(409, "TRIP_CAPACITY_MISSING", "Registra la capacidad del vehÃ­culo")
        edges = [Decimal(0)] * (len(self.path(trip)) - 1)
        incomplete = False
        for row in self.stages(trip_id=trip.id):
            load = self.db.get(Load, row.id_carga)
            if load.deleted_at or row.estado == "cancelado":
                continue
            weight = load.gross_weight_kg or load.net_weight_kg
            if weight is None:
                raise ApiError(
                    409,
                    "TRIP_LOAD_WEIGHT_MISSING",
                    "Registra peso neto o bruto antes de asignar la carga",
                )
            incomplete = incomplete or load.gross_weight_kg is None
            start, end = self.interval(trip, row.origen_id, row.destino_id)
            for i in range(start, end):
                edges[i] += Decimal(weight)
        peak = max(edges, default=Decimal(0))
        if peak > vehicle.capacity_kg:
            raise ApiError(
                409,
                "TRIP_CAPACITY_EXCEEDED",
                "La carga simultÃ¡nea en un tramo supera la capacidad del vehÃ­culo",
                {"peso_kg": str(peak), "capacidad_kg": vehicle.capacity_kg},
            )
        return peak, incomplete

    def sync(self, load):
        rows = self.stages(load_id=load.id)
        if load.status == LoadStatus.CANCELED:
            return
        active = next((r for r in rows if r.estado == "en_transito"), None)
        pending = next((r for r in rows if r.estado == "pendiente"), None)
        done = [r for r in rows if r.estado == "completado"]
        load.trip_id = active.id_viaje if active else pending.id_viaje if pending else None
        load.status = (
            LoadStatus.IN_TRANSIT
            if active
            else LoadStatus.ASSIGNED
            if pending
            else LoadStatus.DELIVERED
            if rows and len(done) == len(rows) and rows[-1].destino_id == load.destino_id
            else LoadStatus.PENDING
        )

    def plan(self, load_id, requested, actor_id, commit=True):
        load = self.db.scalar(
            select(Load).where(Load.id == load_id, Load.deleted_at.is_(None)).with_for_update()
        )
        if not load or load.status == LoadStatus.CANCELED:
            raise ApiError(409, "LOAD_UNAVAILABLE", "La carga no estÃ¡ disponible")
        client = self.db.get(Client, load.client_id)
        if not client or client.deleted_at or client.status not in {"activo", "activa"}:
            raise ApiError(409, "CLIENT_INACTIVE", "La carga necesita un cliente activo")
        if not load.origen_id or not load.destino_id:
            raise ApiError(
                422,
                "LOAD_CITIES_REQUIRED",
                "Selecciona las ciudades de origen y destino de la carga",
            )
        old = self.stages(load_id=load_id)
        if len({r.viaje_id for r in requested}) != len(requested):
            raise ApiError(
                422, "STAGE_TRIP_DUPLICATE", "Un viaje no puede repetirse en el plan de una carga"
            )
        trip_ids = sorted({r.viaje_id for r in requested} | {r.id_viaje for r in old})
        trips = {
            t.id: t
            for t in self.db.scalars(
                select(Trip).where(Trip.id.in_(trip_ids)).order_by(Trip.id).with_for_update()
            ).all()
        }
        fixed = [r for r in old if r.estado != "pendiente"]
        if len(requested) < len(fixed) or any(
            (r.id_viaje, r.origen_id, r.destino_id)
            != (requested[i].viaje_id, requested[i].origen_id, requested[i].destino_id)
            for i, r in enumerate(fixed)
        ):
            raise ApiError(
                409,
                "STAGE_IMMUTABLE",
                "Conserva las etapas iniciadas o completadas al principio del plan",
            )
        previous = None
        for i, row in enumerate(requested):
            trip = trips.get(row.viaje_id)
            if not trip or trip.deleted_at:
                raise ApiError(422, "TRIP_NOT_FOUND", "El viaje no existe")
            route = self.db.get(Route, trip.route_id)
            if i >= len(fixed) and (not route or route.deleted_at or route.status != "activa"):
                raise ApiError(409, "ROUTE_INACTIVE", "Selecciona un viaje con ruta activa")
            if i >= len(fixed) and trip.status != TripStatus.SCHEDULED:
                raise ApiError(
                    409, "TRIP_NOT_SCHEDULED", "Las etapas nuevas requieren viajes programados"
                )
            if row.origen_id != (requested[i - 1].destino_id if i else load.origen_id):
                raise ApiError(
                    422,
                    "STAGE_DISCONTINUITY",
                    "El origen de cada etapa debe coincidir con el destino de la anterior",
                )
            if i and requested[i - 1].destino_id == load.destino_id:
                raise ApiError(
                    422, "STAGE_AFTER_DESTINATION", "La carga ya llegÃ³ a su destino final"
                )
            self.interval(trip, row.origen_id, row.destino_id)
            if previous and utc(previous.scheduled_end_at) > utc(trip.scheduled_start_at):
                raise ApiError(
                    422,
                    "STAGE_SCHEDULE_OVERLAP",
                    "Los viajes de una carga deben respetar el orden temporal",
                )
            previous = trip
        try:
            self.db.execute(
                delete(LoadStage).where(
                    LoadStage.id_carga == load_id, LoadStage.estado == "pendiente"
                )
            )
            self.db.flush()
            for i, row in enumerate(requested[len(fixed) :], len(fixed) + 1):
                self.db.add(
                    LoadStage(
                        id_carga=load_id,
                        id_viaje=row.viaje_id,
                        orden=i,
                        origen_id=row.origen_id,
                        destino_id=row.destino_id,
                        estado="pendiente",
                        created_by=actor_id,
                        data={},
                    )
                )
            self.db.flush()
            for trip in trips.values():
                if not trip.deleted_at:
                    self.capacity(trip)
            self.sync(load)
            if commit:
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return [self.serialize(r) for r in self.stages(load_id=load_id)]

    def compatible(self, load_id, origin=None):
        load = self.db.get(Load, load_id)
        if not load or load.deleted_at:
            raise ApiError(404, "LOAD_NOT_FOUND", "Carga no encontrada")
        rows = self.stages(load_id=load_id)
        start = origin or (rows[-1].destino_id if rows else load.origen_id)
        result = []
        for trip in self.db.scalars(
            select(Trip).where(Trip.deleted_at.is_(None), Trip.status == TripStatus.SCHEDULED)
        ).all():
            if any(r.id_viaje == trip.id for r in rows):
                continue
            if rows and utc(self.db.get(Trip, rows[-1].id_viaje).scheduled_end_at) > utc(
                trip.scheduled_start_at
            ):
                continue
            try:
                path = self.path(trip)
                if start not in path[:-1]:
                    continue
                destinations = path[path.index(start) + 1 :]
                result.append(
                    dict(
                        viaje_id=trip.id,
                        codigo=trip.code,
                        origen_id=start,
                        destinos_ids=destinations,
                        salida=trip.scheduled_start_at,
                        llegada=trip.scheduled_end_at,
                    )
                )
            except ApiError:
                continue
        return result

    def transition(self, load_id, stage_id, target):
        self.db.scalar(select(Load).where(Load.id == load_id).with_for_update())
        row = self.db.get(LoadStage, stage_id)
        if not row or row.id_carga != load_id:
            raise ApiError(404, "STAGE_NOT_FOUND", "Etapa no encontrada")
        trip = self.db.scalar(select(Trip).where(Trip.id == row.id_viaje).with_for_update())
        if trip.status not in {TripStatus.IN_PROGRESS, TripStatus.INCIDENT}:
            raise ApiError(409, "TRIP_NOT_RUNNING", "Inicia el viaje antes de mover la carga")
        rows = self.stages(load_id=load_id)
        if any(r.orden < row.orden and r.estado != "completado" for r in rows):
            raise ApiError(409, "PREVIOUS_STAGE_PENDING", "Completa la etapa anterior primero")
        now = datetime.now(timezone.utc)
        if target == "en_transito" and row.estado == "pendiente":
            row.estado = target
            row.salida_real = now
        elif target == "completado" and row.estado == "en_transito":
            row.estado = target
            row.llegada_real = now
        else:
            raise ApiError(409, "STAGE_TRANSITION_INVALID", "TransiciÃ³n de etapa no permitida")
        self.db.flush()
        self.sync(self.db.get(Load, load_id))
        self.db.commit()
        return self.serialize(row)
