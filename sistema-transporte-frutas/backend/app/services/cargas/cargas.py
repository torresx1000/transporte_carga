from datetime import date, datetime
import unicodedata
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.errors import ApiError
from app.models.entities import Client, Load, ReturnBalanceCut, Trip
from app.models.cargas.cargas import LoadStage
from app.models.rutas.rutas import City
from app.models.enums import LoadStatus
from app.repositories.records import RecordRepository
from app.schemas.cargas.cargas import CargaResponse, CargaExtras
from app.services.etapas.etapas import EtapasService

LIMA_TZ = ZoneInfo("America/Lima")

LOAD_FIELDS = {
    "origen_id": "origen_id",
    "destino_id": "destino_id",
    "jabas_despachadas": "jabas_dispatched",
    "codigo": "code",
    "cliente_id": "client_id",
    "viaje_id": "trip_id",
    "estado": "status",
    "prioridad": "priority",
    "producto": "product",
    "variedad": "variety",
    "cantidad": "quantity",
    "unidad": "unit",
    "peso_neto_total_kg": "net_weight_kg",
    "peso_bruto_total_kg": "gross_weight_kg",
    "procedencia": "origin",
    "destino": "destination",
    "fecha_recojo": "pickup_date",
    "fecha_entrega": "delivery_date",
    "monto_cobrar_centimos": "charge_amount_minor",
    "moneda": "currency",
}


class CargaService:
    def __init__(self, db):
        self.db = db
        self.repo = RecordRepository(db, Load)

    def item(self, id):
        item = self.repo.get(id)
        if not item:
            raise ApiError(404, "LOAD_NOT_FOUND", "Carga no encontrada")
        return item

    def _response(self, item):
        values = {k: getattr(item, v) for k, v in LOAD_FIELDS.items()}
        values.update({k: (item.data or {}).get(k) for k in CargaExtras.model_fields})
        return CargaResponse.model_validate(
            dict(
                **values,
                id=item.id,
                peso_incompleto=item.gross_weight_kg is None,
                etapas=[
                    EtapasService(self.db).serialize(row)
                    for row in EtapasService(self.db).stages(load_id=item.id)
                ],
                created_at=item.created_at,
                updated_at=item.updated_at,
                created_by=item.created_by,
                periodo_retorno_id=item.balance_period_id,
            )
        )

    def list(self, page, page_size, q, **filters):
        mapped = {
            k: (v, filters[k])
            for k, v in {"estado": "status", "cliente_id": "client_id"}.items()
            if filters.get(k)
        }
        total, items = self.repo.list_configured(
            page,
            page_size,
            q,
            ("code", "product", "variety", "origin", "destination", "client.name"),
            mapped,
        )
        if filters.get("viaje_id"):
            ids = set(
                self.db.scalars(
                    select(LoadStage.id_carga).where(LoadStage.id_viaje == filters["viaje_id"])
                ).all()
            )
            # Filter via stage membership before pagination.
            from sqlalchemy import func

            query = select(Load).where(Load.deleted_at.is_(None), Load.id.in_(ids))
            for _, (column, value) in mapped.items():
                query = query.where(getattr(Load, column) == value)
            if q:
                query = query.where(Load.code.ilike(f"%{q}%"))
            total = self.db.scalar(select(func.count()).select_from(query.subquery()))
            items = self.db.scalars(
                query.order_by(Load.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        return dict(
            items=[self._response(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )

    def get(self, id):
        return self._response(self.item(id))

    def validate(self, values):
        client = self.db.get(Client, values["cliente_id"])
        if not client or client.deleted_at or client.status not in {"activo", "activa"}:
            raise ApiError(
                409, "CLIENT_INACTIVE", "Selecciona un cliente activo", {"field": "cliente_id"}
            )
        for key in ("origen_id", "destino_id"):
            if not values.get(key) or not self.db.get(City, values[key]):
                raise ApiError(
                    422, "LOAD_CITY_REQUIRED", "Selecciona una ciudad existente", {"field": key}
                )
        if values["origen_id"] == values["destino_id"]:
            raise ApiError(
                422,
                "LOAD_ENDPOINTS",
                "Origen y destino deben ser diferentes",
                {"field": "destino_id"},
            )
        if (
            values.get("fecha_recojo")
            and values.get("fecha_entrega")
            and str(values["fecha_entrega"]) < str(values["fecha_recojo"])
        ):
            raise ApiError(
                422,
                "LOAD_DATES",
                "La entrega no puede ser anterior al recojo",
                {"field": "fecha_entrega"},
            )
        net, gross = values.get("peso_neto_total_kg"), values.get("peso_bruto_total_kg")
        if net and gross and float(gross) < float(net):
            raise ApiError(
                422,
                "LOAD_WEIGHTS",
                "El peso bruto no puede ser menor al neto",
                {"field": "peso_bruto_total_kg"},
            )

    @staticmethod
    def _city_code(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        letters = "".join(character for character in ascii_value.upper() if character.isalpha())
        return (letters[:3] or "XXX").ljust(3, "X")

    def _next_code(self, values) -> str:
        pickup_date = values.get("fecha_recojo") or datetime.now(LIMA_TZ).date()
        if isinstance(pickup_date, str):
            pickup_date = date.fromisoformat(pickup_date)
        origin = self._city_code(values["procedencia"])
        destination = self._city_code(values["destino"])
        prefix = f"CAR-{pickup_date:%d_%m}_{origin}-{destination}"
        # Serialize assignments for the same city pair while choosing the number.
        city_ids = sorted({values["origen_id"], values["destino_id"]})
        self.db.scalars(
            select(City.id_ciudad)
            .where(City.id_ciudad.in_(city_ids))
            .order_by(City.id_ciudad)
            .with_for_update()
        ).all()
        # Count all matching codes, including those from prior years, because the
        # requested visible format omits the year and the database code is unique.
        matching_codes = self.db.scalars(
            select(Load.id).where(Load.code.startswith(prefix, autoescape=True)).with_for_update()
        ).all()
        sequence = len(matching_codes)
        return f"{prefix}-{sequence + 1}"

    def create(self, payload, created_by):
        values = payload.model_dump()
        client = self.db.scalar(
            select(Client)
            .where(Client.id == values["cliente_id"], Client.deleted_at.is_(None))
            .with_for_update()
        )
        if not client or client.status not in {"activo", "activa"}:
            raise ApiError(
                409, "CLIENT_INACTIVE", "Selecciona un cliente activo", {"field": "cliente_id"}
            )
        self.validate(values)
        cut = self.db.scalar(
            select(ReturnBalanceCut)
            .where(ReturnBalanceCut.client_id == values["cliente_id"])
            .order_by(ReturnBalanceCut.sequence.desc())
            .limit(1)
        )
        values["codigo"] = self._next_code(values)
        if values["jabas_despachadas"] is None:
            values["jabas_despachadas"] = payload.cantidad if payload.unidad == "jaba" else 0
        item = Load(
            **{column: values[key] for key, column in LOAD_FIELDS.items() if key in values},
            status=LoadStatus.PENDING,
            balance_period_id=cut.id if cut else None,
            created_by=created_by,
            data=payload.model_dump(mode="json"),
        )
        self.db.add(item)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ApiError(
                409, "LOAD_DUPLICATE", "El código ya pertenece a otra carga", {"field": "codigo"}
            ) from None
        return self._response(item)

    def update(self, id, payload, user_id, role):
        item = self.db.scalar(
            select(Load).where(Load.id == id, Load.deleted_at.is_(None)).with_for_update()
        )
        if not item:
            raise ApiError(404, "LOAD_NOT_FOUND", "Carga no encontrada")
        rows = EtapasService(self.db).stages(load_id=id)
        changes = payload.model_dump(exclude_unset=True)
        changes.pop("motivo", None)
        if any(r.estado != "pendiente" for r in rows):
            raise ApiError(
                409,
                "LOAD_STARTED",
                "No se puede modificar la carga después de iniciar su transporte",
            )
        if rows and {"origen_id", "destino_id"} & changes.keys():
            if any(
                changes.get(k, getattr(item, k)) != getattr(item, k)
                for k in ("origen_id", "destino_id")
            ):
                raise ApiError(
                    409, "LOAD_PLANNED", "Retira el plan de etapas antes de cambiar los extremos"
                )
        values = {k: getattr(item, v) for k, v in LOAD_FIELDS.items()}
        values.update(changes)
        self.validate(values)
        try:
            for row in sorted(rows, key=lambda r: r.id_viaje):
                self.db.scalar(select(Trip).where(Trip.id == row.id_viaje).with_for_update())
            for key, value in changes.items():
                if key in LOAD_FIELDS:
                    setattr(item, LOAD_FIELDS[key], value)
            item.data = {**(item.data or {}), **payload.model_dump(mode="json", exclude_unset=True)}
            self.db.flush()
            for row in rows:
                EtapasService(self.db).capacity(self.db.get(Trip, row.id_viaje))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self._response(item)

    def delete(self, id):
        item = self.item(id)
        if EtapasService(self.db).stages(load_id=id):
            raise ApiError(
                409,
                "LOAD_ASSIGNED",
                "Retira las etapas pendientes antes de eliminar; el historial iniciado se conserva",
            )
        self.repo.delete(item)

    def transition(self, id, payload):
        item = self.item(id)
        rows = EtapasService(self.db).stages(load_id=id)
        if payload.estado == LoadStatus.CANCELED:
            if any(r.estado != "pendiente" for r in rows):
                raise ApiError(409, "LOAD_STARTED", "La carga ya inició su transporte")
            from sqlalchemy import delete

            self.db.execute(delete(LoadStage).where(LoadStage.id_carga == id))
            item.trip_id = None
            item.status = LoadStatus.CANCELED
            self.db.commit()
            return self._response(item)
        raise ApiError(
            409,
            "LOAD_AUTOMATIC_STATUS",
            "El estado de la carga se actualiza al completar sus etapas",
        )
