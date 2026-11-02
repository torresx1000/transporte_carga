from fastapi import HTTPException
from pydantic import ValidationError
from app.models.vehiculos.vehiculos import Vehicle
from app.schemas.mantenimiento.mantenimiento import MaintenanceData, SERVICE_TYPES
from app.services.records import RecordService


def validate_maintenance(db, data, existing=None):
    nullable = {
        "fecha_ingreso",
        "fecha_inicio",
        "fecha_fin",
        "kilometraje",
        "duracion_estimada_horas",
    }
    values = {
        key: (None if value == "" and key in nullable else value) for key, value in data.items()
    }
    try:
        parsed = MaintenanceData.model_validate(values)
    except ValidationError as exc:
        raise HTTPException(422, "; ".join(error["msg"] for error in exc.errors())) from exc
    if parsed.tipo not in SERVICE_TYPES and (
        existing is None or parsed.tipo != existing.get("tipo")
    ):
        raise HTTPException(422, "Selecciona un tipo de servicio del catálogo")
    if existing is None and parsed.duracion_estimada_horas is None:
        raise HTTPException(422, "Indica la duración estimada del mantenimiento en horas")
    vehicle = db.get(Vehicle, parsed.vehiculo_id)
    if not vehicle or vehicle.deleted_at is not None:
        raise HTTPException(422, "El vehículo seleccionado no existe o está dado de baja")
    if vehicle.status == "inactivo" and (
        existing is None or parsed.vehiculo_id != existing.get("vehiculo_id")
    ):
        raise HTTPException(409, "Selecciona un vehículo activo")
    result = parsed.model_dump(mode="json")
    result["vehiculo_placa"] = vehicle.plate
    result["vehiculo_codigo"] = vehicle.fleet_code
    result["duracion_real_horas"] = (
        round((parsed.fecha_fin - parsed.fecha_inicio).total_seconds() / 3600, 2)
        if parsed.fecha_inicio and parsed.fecha_fin
        else None
    )
    return result


class MantenimientoService(RecordService):
    pass
