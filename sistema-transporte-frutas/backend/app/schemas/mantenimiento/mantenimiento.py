from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.common import RecordCreate, RecordUpdate

SERVICE_TYPES = (
    "Mantenimiento preventivo",
    "Reparación correctiva",
    "Neumáticos y alineación",
    "Sistema eléctrico",
    "Otros",
)


class MaintenanceData(BaseModel):
    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)
    vehiculo_id: str = Field(min_length=1)
    tipo: str = Field(min_length=1)
    estado: Literal["programado", "en_proceso", "completado", "cancelado"] = "programado"
    duracion_estimada_horas: Decimal | None = Field(default=None, gt=0, le=8760)
    fecha_ingreso: datetime | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    kilometraje: int | None = Field(default=None, ge=0)
    prioridad: Literal["baja", "normal", "alta", "urgente"] = "normal"
    costo_centimos: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.fecha_fin and not self.fecha_inicio:
            raise ValueError("Indica el inicio antes de registrar el fin del mantenimiento")
        for start, end in (
            (self.fecha_ingreso, self.fecha_inicio),
            (self.fecha_inicio, self.fecha_fin),
        ):
            if start and end:
                try:
                    valid = end >= start
                except TypeError:
                    raise ValueError("Las fechas deben utilizar la misma zona horaria") from None
                if not valid:
                    raise ValueError("Las fechas de ingreso, inicio y fin deben estar en orden")
        return self


MantenimientoCreate = RecordCreate
MantenimientoUpdate = RecordUpdate
