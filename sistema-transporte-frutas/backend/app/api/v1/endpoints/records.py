from datetime import datetime
from dataclasses import dataclass, field as dataclass_field
from importlib import import_module
import re
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.permissions import require_roles
from app.models.entities import Client, MODEL_BY_MODULE, ReturnAllocation, ReturnBalanceCut, User
from app.repositories.records import RecordRepository
from app.schemas.common import RecordCreate, RecordUpdate
from app.schemas.responses import CodeSuggestionResponse, PageResponse, RESOURCE_RESPONSE_MODELS


admin_or_operator = require_roles("admin", "operador")


@dataclass(frozen=True)
class ResourceContract:
    """Schema-driven contract for resources migrated to the direct-body CRUD factory."""

    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    response_schema: type[BaseModel]
    search_fields: tuple[str, ...] = ()
    filters: dict[str, str] = dataclass_field(default_factory=dict)
    unique_fields: dict[str, str] = dataclass_field(default_factory=dict)
    permissions: dict[str, tuple[str, ...]] = dataclass_field(default_factory=dict)
    column_fields: dict[str, str] = dataclass_field(default_factory=dict)
    code_suggestion: tuple[str, str, int, int] | None = None
    service_factory: Callable[[Session], Any] | None = None
    allow_reactivate: bool = False
    prefix: str | None = None
    update_actor_context: bool = False
    delete_guard: Callable[[Session, str], None] | None = None


def _schema_router_for(module: str, model: type, contract: ResourceContract) -> APIRouter:
    if contract.create_schema.model_config.get("extra") != "forbid":
        raise ValueError(f"{module}: create_schema debe declarar extra='forbid'")
    if contract.update_schema.model_config.get("extra") != "forbid":
        raise ValueError(f"{module}: update_schema debe declarar extra='forbid'")

    router = APIRouter(prefix=contract.prefix or f"/{module}", tags=[module])

    def access(action: str):
        roles = contract.permissions.get(
            action, ("admin",) if action in {"delete", "reactivate"} else ("admin", "operador")
        )
        return require_roles(*roles)

    def service_for(db: Session):
        return contract.service_factory(db) if contract.service_factory else None

    def record_payload(item: Any, db: Session | None = None) -> dict[str, Any]:
        allowed = set(contract.response_schema.model_fields)
        payload = {key: value for key, value in (item.data or {}).items() if key in allowed}
        for response_field, model_field in contract.column_fields.items():
            value = getattr(item, model_field, None)
            if value is not None:
                payload[response_field] = value
        if db is not None and module in {"conductores", "vehiculos"}:
            from app.models.entities import Trip
            from app.models.enums import TripStatus

            reference_field = "driver_id" if module == "conductores" else "vehicle_id"
            active_trip = db.scalar(
                select(Trip.id)
                .where(
                    getattr(Trip, reference_field) == item.id,
                    Trip.deleted_at.is_(None),
                    Trip.status.in_([TripStatus.IN_PROGRESS, TripStatus.INCIDENT]),
                )
                .limit(1)
            )
            if active_trip:
                payload["estado"] = "en_viaje"
        return {
            **payload,
            "id": item.id,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "created_by": item.created_by,
        }

    def find_unique_conflict(db: Session, values: dict[str, Any], current_id: str | None = None):
        for request_field, model_field in contract.unique_fields.items():
            value = values.get(request_field)
            if value is None:
                continue
            existing = db.scalar(select(model).where(getattr(model, model_field) == value))
            if existing is None or existing.id == current_id:
                continue
            if existing.deleted_at is not None:
                raise ApiError(
                    409,
                    "RESOURCE_ARCHIVED",
                    "El dato pertenece a un registro dado de baja.",
                    {"field": request_field, "record_id": existing.id},
                )
            raise ApiError(
                409,
                "RESOURCE_DUPLICATE",
                "Ya existe un registro con este dato.",
                {"field": request_field, "record_id": existing.id},
            )

    def integrity_conflict(db: Session, values: dict[str, Any], current_id: str | None = None):
        find_unique_conflict(db, values, current_id)
        first = next(iter(contract.unique_fields), "")
        raise ApiError(
            409,
            "RESOURCE_CONFLICT",
            "No se pudo guardar el registro porque existe un conflicto con sus datos.",
            {"field": first} if first else {},
        )

    @router.get("", response_model=PageResponse[contract.response_schema])
    def list_schema_records(
        request: Request,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        q: str | None = Query(default=None, max_length=100),
        estado: str | None = None,
        tipo: str | None = None,
        db: Session = Depends(get_db),
        user: User = Depends(access("list")),
    ):
        service = service_for(db)
        filter_values = {name: request.query_params.get(name) for name in contract.filters}
        if service is not None:
            result = service.list(page, page_size, q, **filter_values)
            result["page_size"] = page_size
            return result
        repo = RecordRepository(db, model)
        mapped_filters = {
            name: (contract.filters[name], value) for name, value in filter_values.items()
        }
        total, items = repo.list_configured(
            page, page_size, q, contract.search_fields, mapped_filters
        )
        return {
            "items": [record_payload(item, db) for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    if contract.code_suggestion is not None:
        code_field, prefix, width, maximum = contract.code_suggestion

        @router.get("/siguiente-codigo", response_model=CodeSuggestionResponse)
        def suggest_next_code(
            db: Session = Depends(get_db),
            user: User = Depends(access("list")),
        ):
            column = getattr(model, code_field)
            used = db.scalars(select(column)).all()
            numbers = []
            pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$", re.IGNORECASE)
            for value in used:
                match = pattern.fullmatch(str(value or ""))
                if match:
                    numbers.append(int(match.group(1)))
            next_number = max(numbers, default=0) + 1
            if next_number > maximum:
                raise ApiError(
                    409, "CODE_SEQUENCE_EXHAUSTED", "Se agotó la secuencia de códigos disponibles."
                )
            return {"code": f"{prefix}-{next_number:0{max(width, len(str(next_number)))}d}"}

    @router.post("", status_code=201, response_model=contract.response_schema)
    def create_schema_record(
        payload: contract.create_schema,
        db: Session = Depends(get_db),
        user: User = Depends(access("create")),
    ):
        service = service_for(db)
        if service is not None:
            return service.create(payload, user.id)
        data = payload.model_dump(mode="json")
        if module == "vehiculos":
            if data.get("tiene_remolque") and not data.get("placa_remolque"):
                raise ApiError(422, "TRAILER_PLATE_REQUIRED", "Ingresa la placa del remolque.")
            if not data.get("tiene_remolque"):
                data["placa_remolque"] = None
        find_unique_conflict(db, data)
        values = _column_values(module, data)
        values.update(data=data, created_by=user.id)
        item = model(**values)
        db.add(item)
        try:
            db.commit()
            db.refresh(item)
        except IntegrityError:
            db.rollback()
            integrity_conflict(db, data)
        return record_payload(item, db)

    @router.get("/{record_id}", response_model=contract.response_schema)
    def get_schema_record(
        record_id: str,
        db: Session = Depends(get_db),
        user: User = Depends(access("read")),
    ):
        service = service_for(db)
        if service is not None:
            return service.get(record_id)
        item = RecordRepository(db, model).get(record_id)
        if item is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "Registro no encontrado")
        return record_payload(item, db)

    @router.patch("/{record_id}", response_model=contract.response_schema)
    @router.put("/{record_id}", response_model=contract.response_schema)
    def update_schema_record(
        record_id: str,
        payload: contract.update_schema,
        db: Session = Depends(get_db),
        user: User = Depends(access("update")),
    ):
        service = service_for(db)
        if service is not None:
            if contract.update_actor_context:
                return service.update(record_id, payload, user.id, user.role)
            return service.update(record_id, payload)
        repo = RecordRepository(db, model)
        item = repo.get(record_id)
        if item is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "Registro no encontrado")
        changes = payload.model_dump(mode="json", exclude_unset=True)
        merged = {**(item.data or {}), **changes}
        if module == "vehiculos":
            if merged.get("tiene_remolque") and not merged.get("placa_remolque"):
                raise ApiError(422, "TRAILER_PLATE_REQUIRED", "Ingresa la placa del remolque.")
            if not merged.get("tiene_remolque"):
                merged["placa_remolque"] = None
        find_unique_conflict(db, merged, item.id)
        item.data = merged
        for field_name, value in _column_values(module, merged).items():
            if hasattr(item, field_name):
                setattr(item, field_name, value)
        try:
            db.commit()
            db.refresh(item)
        except IntegrityError:
            db.rollback()
            integrity_conflict(db, merged, record_id)
        return record_payload(item, db)

    @router.delete("/{record_id}", status_code=204)
    def delete_schema_record(
        record_id: str,
        db: Session = Depends(get_db),
        user: User = Depends(access("delete")),
    ):
        service = service_for(db)
        if service is not None:
            service.delete(record_id)
            return None
        repo = RecordRepository(db, model)
        item = repo.get(record_id)
        if item is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "Registro no encontrado")
        if contract.delete_guard is not None:
            contract.delete_guard(db, record_id)
        repo.delete(item)
        return None

    if contract.allow_reactivate:

        @router.post("/{record_id}/reactivar", response_model=contract.response_schema)
        def reactivate_schema_record(
            record_id: str,
            db: Session = Depends(get_db),
            user: User = Depends(access("reactivate")),
        ):
            service = service_for(db)
            if service is not None:
                return service.reactivate(record_id)
            repo = RecordRepository(db, model)
            item = repo.get_including_archived(record_id)
            if item is None:
                raise ApiError(404, "RESOURCE_NOT_FOUND", "Registro no encontrado")
            if item.deleted_at is None:
                raise ApiError(409, "RESOURCE_NOT_ARCHIVED", "El registro no está dado de baja.")
            values = {
                field: getattr(item, attr, None) for field, attr in contract.column_fields.items()
            }
            find_unique_conflict(db, values, item.id)
            try:
                return record_payload(repo.reactivate(item), db)
            except IntegrityError:
                db.rollback()
                integrity_conflict(db, values, item.id)

    return router


def _column_values(module: str, data: dict[str, Any]) -> dict[str, Any]:
    maps = {
        "clientes": {"name": "nombre", "document": "documento", "status": "estado"},
        "conductores": {
            "name": "nombre",
            "document": "documento",
            "status": "estado",
            "license_number": "licencia",
            "license_category": "categoria_licencia",
            "license_expires_at": "licencia_vence",
            "medical_exam_expires_at": "examen_medico_vence",
        },
        "vehiculos": {
            "fleet_code": "codigo_flota",
            "plate": "placa",
            "vin": "vin",
            "vehicle_type": "tipo",
            "capacity_kg": "capacidad_kg",
            "status": "estado",
            "has_trailer": "tiene_remolque",
            "trailer_plate": "placa_remolque",
        },
        "rutas": {
            "code": "codigo",
            "name": "nombre",
            "origin": "origen",
            "destination": "destino",
            "status": "estado",
            "distance_km": "distancia_km",
            "estimated_duration_minutes": "duracion_minutos",
            "tolls_minor": "peajes_minor",
            "reference_tariff_minor": "tarifa_referencial_minor",
            "currency": "moneda",
        },
        "cargas": {
            "code": "codigo",
            "client_id": "cliente_id",
            "status": "estado",
            "jabas_dispatched": "jabas_despachadas",
        },
        "viajes": {
            "code": "codigo",
            "vehicle_id": "vehiculo_id",
            "driver_id": "conductor_id",
            "status": "estado",
        },
        "retornos": {"client_id": "cliente_id", "load_id": "carga_id", "trip_id": "viaje_id"},
        "documentos": {
            "owner_type": "propietario_tipo",
            "owner_id": "propietario_id",
            "document_type": "tipo",
            "expires_at": "vence_en",
        },
        "gastos": {
            "trip_id": "viaje_id",
            "vehicle_id": "vehiculo_id",
            "amount": "monto_centimos",
            "category": "categoria",
        },
        "combustible": {
            "trip_id": "viaje_id",
            "vehicle_id": "vehiculo_id",
            "liters_milli": "litros_milesimas",
            "price_cents": "precio_centimos",
            "odometer": "odometro",
        },
        "mantenimiento": {"vehicle_id": "vehiculo_id", "status": "estado"},
        "pagos": {"client_id": "cliente_id", "amount": "monto_centimos", "status": "estado"},
        "configuracion": {"key": "clave"},
    }
    values = {key: data[source] for key, source in maps.get(module, {}).items() if source in data}
    for key in ("license_expires_at", "medical_exam_expires_at"):
        if key in values and isinstance(values[key], str):
            values[key] = datetime.fromisoformat(values[key]).date()
    defaults = {
        "cargas": {
            "code": f"CAR-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "jabas_dispatched": 0,
        },
        "viajes": {"code": f"VJ-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"},
        "retornos": {"client_id": data.get("cliente_id")},
        "configuracion": {"key": f"param-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"},
    }
    for key, value in defaults.get(module, {}).items():
        if key not in values and value is not None:
            values[key] = value
    if module == "cargas":
        if "prioridad" in data:
            values["priority"] = data["prioridad"]
        unit = str(data.get("unidad_peso", "kg")).lower()
        factor = 1000 if unit in {"t", "ton", "tonelada", "toneladas"} else 1
        if "peso_neto" in data or "peso" in data:
            data["peso_neto_kg"] = float(data.get("peso_neto", data.get("peso", 0))) * factor
        if "peso_bruto" in data:
            data["peso_bruto_kg"] = float(data["peso_bruto"]) * factor
        data.setdefault("jabas_despachadas", 0)
    if module == "retornos":
        values["returned_total"] = (
            int(data.get("paquetes_3", 0)) * 3
            + int(data.get("paquetes_2", 0)) * 2
            + int(data.get("sueltas", 0))
        )
    return values


def _legacy_router_for(module: str, model: type):
    r = APIRouter(prefix=f"/{module}", tags=[module])
    module_class_names = {
        "clientes": "Cliente",
        "conductores": "Conductor",
        "vehiculos": "Vehiculo",
        "rutas": "Ruta",
        "cargas": "Carga",
        "viajes": "Viaje",
        "cotizaciones": "Cotizacion",
        "retornos": "Retorno",
        "documentos": "Documento",
        "gastos": "Gasto",
        "combustible": "Combustible",
        "mantenimiento": "Mantenimiento",
        "pagos": "Pago",
        "configuracion": "Configuracion",
    }
    class_name = module_class_names[module]
    response_schema = RESOURCE_RESPONSE_MODELS[module]
    page_response_schema = PageResponse[response_schema]
    repository_class = getattr(
        import_module(f"app.repositories.{module}"), f"{class_name}Repository"
    )
    service_class = getattr(import_module(f"app.services.{module}"), f"{class_name}Service")

    def record_data(item, db):
        data = dict(item.data)
        if module == "cargas":
            data["periodo_retorno_id"] = item.balance_period_id
        if module == "mantenimiento":
            from app.models.vehiculos.vehiculos import Vehicle

            vehicle = db.get(Vehicle, item.vehicle_id)
            data.update(vehiculo_id=item.vehicle_id, estado=item.status)
            if vehicle:
                data.update(vehiculo_placa=vehicle.plate, vehiculo_codigo=vehicle.fleet_code)
        return data

    read_access = require_roles("admin") if module == "configuracion" else admin_or_operator
    write_access = require_roles("admin") if module == "configuracion" else admin_or_operator

    @r.get("", response_model=page_response_schema)
    def list_records(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        estado: str | None = None,
        cliente_id: str | None = None,
        vehiculo_id: str | None = None,
        conductor_id: str | None = None,
        q: str | None = None,
        db: Session = Depends(get_db),
        user: User = Depends(read_access),
    ):
        filters = {"status": estado} if estado and hasattr(model, "status") else {}
        for field, value in (
            ("client_id", cliente_id),
            ("vehicle_id", vehiculo_id),
            ("driver_id", conductor_id),
        ):
            if value and hasattr(model, field):
                filters[field] = value
        if q:
            fields = [
                getattr(model, field)
                for field in ("name", "code", "plate", "origin", "destination", "document")
                if hasattr(model, field)
            ]
            if fields:
                filters["_search"] = q
        result = service_class(repository_class(db, model)).list(page, page_size, filters)
        result["page_size"] = page_size
        result["items"] = [
            {
                "id": item.id,
                **record_data(item, db),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "created_by": item.created_by,
            }
            for item in result["items"]
        ]
        return result

    @r.post("", status_code=201, response_model=response_schema)
    def create_record(
        payload: RecordCreate, db: Session = Depends(get_db), user: User = Depends(write_access)
    ):
        data = payload.data
        if module in {"combustible", "gastos"}:
            from app.models.entities import Trip

            trip_id = data.get("viaje_id")
            if not trip_id:
                raise HTTPException(422, "Selecciona el viaje al que corresponde el costo.")
            trip = db.get(Trip, str(trip_id))
            if not trip or trip.deleted_at:
                raise HTTPException(422, "El viaje seleccionado no existe o está archivado.")
            if not trip.vehicle_id:
                raise HTTPException(422, "El viaje debe tener un vehículo asignado.")
            # The trip is the source of truth so costs cannot be attributed to another truck.
            data["vehiculo_id"] = trip.vehicle_id
        if module == "mantenimiento":
            from app.services.mantenimiento.mantenimiento import validate_maintenance

            data = validate_maintenance(db, data)
        values = _column_values(module, data)
        if module == "cargas" and data.get("cliente_id"):
            client_id = str(data["cliente_id"])
            client = db.scalar(
                select(Client)
                .where(Client.id == client_id, Client.deleted_at.is_(None))
                .with_for_update()
            )
            if not client:
                raise HTTPException(422, "El cliente seleccionado no existe o está archivado.")
            cut = db.scalar(
                select(ReturnBalanceCut)
                .where(ReturnBalanceCut.client_id == client_id)
                .order_by(ReturnBalanceCut.sequence.desc())
                .limit(1)
            )
            values["balance_period_id"] = cut.id if cut else None
        if module == "retornos":
            breakdown = data.get("desglose_clientes", [])
            allocation_client_ids = {
                str(row.get("cliente_id"))
                for row in breakdown
                if row.get("cliente_id")
            }
            if not allocation_client_ids and data.get("cliente_id"):
                allocation_client_ids.add(str(data["cliente_id"]))
            locked_clients = db.scalars(
                select(Client)
                .where(
                    Client.id.in_(sorted(allocation_client_ids)),
                    Client.deleted_at.is_(None),
                )
                .order_by(Client.id)
                .with_for_update()
            ).all() if allocation_client_ids else []
            if len(locked_clients) != len(allocation_client_ids):
                raise HTTPException(422, "Uno de los clientes del retorno no existe o está archivado.")
            periods = {}
            for client in locked_clients:
                cut = db.scalar(
                    select(ReturnBalanceCut)
                    .where(ReturnBalanceCut.client_id == client.id)
                    .order_by(ReturnBalanceCut.sequence.desc())
                    .limit(1)
                )
                periods[client.id] = cut.id if cut else None
            if data.get("cliente_id"):
                values["balance_period_id"] = periods.get(str(data["cliente_id"]))
            if data.get("carga_id"):
                load = db.get(MODEL_BY_MODULE["cargas"], str(data["carga_id"]))
                client_id = load.client_id if load else None
                if client_id in periods and load.balance_period_id != periods[client_id]:
                    raise HTTPException(
                        422,
                        "Selecciona una carga del periodo actual; las cargas anteriores al reinicio no se cuentan.",
                    )
            if breakdown:
                allocations = []
                for row in breakdown:
                    total = (
                        int(row.get("paquetes_3", 0)) * 3
                        + int(row.get("paquetes_2", 0)) * 2
                        + int(row.get("sueltas", 0))
                    )
                    if not row.get("cliente_id") or total < 0:
                        raise HTTPException(
                            400, "Cada desglose requiere cliente y cantidades válidas"
                        )
                    client_id = str(row["cliente_id"])
                    allocations.append((client_id, total, periods[client_id]))
                values["returned_total"] = sum(total for _, total, _period_id in allocations)
                data["total_jabas_retornadas"] = values["returned_total"]
            else:
                allocations = []
                data["total_jabas_retornadas"] = values["returned_total"]
        if module == "usuarios":
            raise HTTPException(400, "Usa los endpoints de autenticación para administrar usuarios")
        if module == "documentos" and isinstance(data.get("vence_en"), str):
            values["expires_at"] = datetime.fromisoformat(data["vence_en"])
        values.update(data=data, created_by=user.id)
        try:
            if module == "retornos":
                item = model(**values)
                db.add(item)
                db.flush()
            else:
                item = repository_class(db, model).create(values)
            for client_id, total, period_id in allocations if module == "retornos" else []:
                db.add(
                    ReturnAllocation(
                        return_id=item.id,
                        client_id=client_id,
                        returned_total=total,
                        balance_period_id=period_id,
                        created_by=user.id,
                        data={},
                    )
                )
            if module == "retornos":
                db.commit()
                db.refresh(item)
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                409, "No se pudo crear el registro; revisa sus datos y referencias"
            ) from exc
        response = {
            "id": item.id,
            **record_data(item, db),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "created_by": item.created_by,
        }
        if module == "retornos":
            response["total_jabas_retornadas"] = item.returned_total
        return response

    @r.get("/{record_id}", response_model=response_schema)
    def get_record(
        record_id: str, db: Session = Depends(get_db), user: User = Depends(read_access)
    ):
        item = repository_class(db, model).get(record_id)
        if not item:
            raise HTTPException(404, "Registro no encontrado")
        return {
            "id": item.id,
            **record_data(item, db),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "created_by": item.created_by,
        }

    @r.patch("/{record_id}", response_model=response_schema)
    @r.put("/{record_id}", response_model=response_schema)
    def update_record(
        record_id: str,
        payload: RecordUpdate,
        db: Session = Depends(get_db),
        user: User = Depends(write_access),
    ):
        repo = repository_class(db, model)
        item = repo.get(record_id)
        if not item:
            raise HTTPException(404, "Registro no encontrado")
        data = payload.data or {}
        merged = {**record_data(item, db), **data}
        if module == "mantenimiento":
            from app.services.mantenimiento.mantenimiento import validate_maintenance

            merged = validate_maintenance(db, merged, item.data)
        item.data = merged
        for key, value in _column_values(module, merged).items():
            if hasattr(item, key):
                setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return {
            "id": item.id,
            **record_data(item, db),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "created_by": item.created_by,
        }

    @r.delete("/{record_id}", status_code=204)
    def delete_record(
        record_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))
    ):
        repo = repository_class(db, model)
        item = repo.get(record_id)
        if not item:
            raise HTTPException(404, "Registro no encontrado")
        repo.delete(item)
        return None

    return r


def build_resource_router(module: str, contract: ResourceContract | None = None):
    model = MODEL_BY_MODULE[module]
    if contract is not None:
        return _schema_router_for(module, model, contract)
    return _legacy_router_for(module, model)
