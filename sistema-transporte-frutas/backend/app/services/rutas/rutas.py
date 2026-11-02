from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from app.core.errors import ApiError
from app.models.rutas.rutas import Route, City, RouteStop
from app.repositories.records import RecordRepository
from app.schemas.rutas.rutas import RutaCreate
from app.services.viajes.viajes import guard_reference_deactivation


class RutaService:
    def __init__(self, db):
        self.db = db
        self.repo = RecordRepository(db, Route)

    def item(self, record_id, archived=False):
        item = self.db.get(Route, record_id)
        if not item or (item.deleted_at and not archived):
            raise ApiError(404, "RESOURCE_NOT_FOUND", "Ruta no encontrada")
        return item

    def serialize(self, item):
        city_names = dict(self.db.execute(select(City.id_ciudad, City.nombre)).all())
        data = item.data or {}
        return dict(
            id=item.id,
            codigo=item.code,
            nombre=item.name,
            origen_id=item.origen_id,
            destino_id=item.destino_id,
            origen=city_names[item.origen_id],
            destino=city_names[item.destino_id],
            estado=item.status,
            distancia_km=item.distance_km,
            duracion_minutos=item.estimated_duration_minutes,
            peajes_minor=item.tolls_minor,
            tarifa_referencial_minor=item.reference_tariff_minor,
            moneda=item.currency,
            notas=data.get("notas"),
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by,
            paradas=[
                dict(
                    id_parada=p.id_parada,
                    ciudad_id=p.ciudad_id,
                    ciudad=city_names[p.ciudad_id],
                    orden=p.orden,
                    tiempo_espera=p.tiempo_espera,
                )
                for p in item.stops
            ],
        )

    def list(self, page, page_size, q, **filters):
        mapped = {"estado": ("status", filters.get("estado"))}
        total, items = self.repo.list_configured(
            page, page_size, q, ("code", "name", "origin", "destination"), mapped
        )
        return dict(
            total=total,
            items=[self.serialize(i) for i in items],
            page=page,
            pages=(total + page_size - 1) // page_size,
        )

    def get(self, record_id):
        return self.serialize(self.item(record_id))

    def validate(self, payload, current_id=None):
        values = payload.model_dump(mode="json")
        cities = {city.id_ciudad: city for city in self.db.scalars(select(City)).all()}
        ids = [payload.origen_id, payload.destino_id] + [p.ciudad_id for p in payload.paradas]
        if any(city_id not in cities for city_id in ids):
            raise ApiError(
                422, "CITY_NOT_FOUND", "Selecciona ciudades existentes para toda la ruta"
            )
        if payload.origen_id == payload.destino_id:
            raise ApiError(
                422, "ROUTE_ENDPOINTS", "El origen y el destino deben ser ciudades diferentes"
            )
        orders = [p.orden for p in payload.paradas]
        if len(orders) != len(set(orders)):
            raise ApiError(
                422, "STOP_ORDER_DUPLICATE", "No se puede repetir el orden de una parada"
            )
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ApiError(
                422,
                "STOP_ORDER_SEQUENCE",
                "El orden de las paradas debe comenzar en 1 y ser consecutivo",
            )
        if any(p.ciudad_id in {payload.origen_id, payload.destino_id} for p in payload.paradas):
            raise ApiError(
                422, "STOP_ENDPOINT", "Las paradas solo pueden contener ciudades intermedias"
            )
        duplicate = self.db.scalar(select(Route).where(Route.code == payload.codigo))
        if duplicate and duplicate.id != current_id:
            raise ApiError(
                409,
                "RESOURCE_ARCHIVED" if duplicate.deleted_at else "RESOURCE_DUPLICATE",
                "El código pertenece a otra ruta",
                {"record_id": duplicate.id, "field": "codigo"},
            )
        return values, cities

    def save(self, item, payload):
        values, cities = self.validate(payload, item.id)
        for key, column in {
            "codigo": "code",
            "nombre": "name",
            "estado": "status",
            "origen_id": "origen_id",
            "destino_id": "destino_id",
            "distancia_km": "distance_km",
            "duracion_minutos": "estimated_duration_minutes",
            "peajes_minor": "tolls_minor",
            "tarifa_referencial_minor": "reference_tariff_minor",
            "moneda": "currency",
        }.items():
            setattr(item, column, getattr(payload, key))
        item.origin = cities[payload.origen_id].nombre
        item.destination = cities[payload.destino_id].nombre
        item.data = {
            **(item.data or {}),
            **values,
            "origen": item.origin,
            "destino": item.destination,
        }
        try:
            self.db.add(item)
            self.db.flush()
            # Delete before inserting so reordering never temporarily violates UNIQUE(route, order).
            self.db.execute(delete(RouteStop).where(RouteStop.id_ruta == item.id))
            self.db.flush()
            for stop in sorted(payload.paradas, key=lambda p: p.orden):
                self.db.add(RouteStop(id_ruta=item.id, **stop.model_dump()))
            self.db.commit()
            self.db.expire(item)
            return self.serialize(item)
        except IntegrityError as exc:
            self.db.rollback()
            raise ApiError(
                409, "ROUTE_CONFLICT", "No se pudo guardar la ruta; revisa código, ciudades y orden"
            ) from exc

    def create(self, payload, actor_id):
        return self.save(Route(created_by=actor_id, data={}), payload)

    def update(self, record_id, payload):
        item = self.item(record_id)
        current = self.serialize(item)
        allowed = RutaCreate.model_fields
        values = {k: v for k, v in current.items() if k in allowed}
        values["paradas"] = [
            {k: p[k] for k in ("ciudad_id", "orden", "tiempo_espera")} for p in current["paradas"]
        ]
        values.update(payload.model_dump(mode="json", exclude_unset=True))
        if any(
            values[k]
            != (
                {
                    "origen_id": current["origen_id"],
                    "destino_id": current["destino_id"],
                    "paradas": [
                        {key: p[key] for key in ("ciudad_id", "orden", "tiempo_espera")}
                        for p in current["paradas"]
                    ],
                }
            )[k]
            for k in ("origen_id", "destino_id", "paradas")
        ):
            from app.models.cargas.cargas import LoadStage
            from app.models.entities import Trip

            used = self.db.scalar(
                select(LoadStage.id)
                .join(Trip, Trip.id == LoadStage.id_viaje)
                .where(Trip.route_id == record_id)
                .limit(1)
            )
            if used:
                raise ApiError(
                    409,
                    "ROUTE_HAS_STAGES",
                    "La ruta tiene etapas de carga; conserva su recorrido y crea otra ruta para cambiarlo",
                )
        if values.get("estado") == "inactiva" and item.status != "inactiva":
            guard_reference_deactivation(self.db, "rutas", record_id)
        return self.save(item, RutaCreate.model_validate(values))

    def delete(self, record_id):
        item = self.item(record_id)
        guard_reference_deactivation(self.db, "rutas", record_id)
        self.repo.delete(item)

    def reactivate(self, record_id):
        item = self.item(record_id, archived=True)
        if not item.deleted_at:
            raise ApiError(409, "RESOURCE_NOT_ARCHIVED", "La ruta no está dada de baja")
        return self.serialize(self.repo.reactivate(item))
