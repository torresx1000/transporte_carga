"""SQLAlchemy model registry. Feature model implementations live in sibling modules."""

from app.models.combustible import Fueling
from app.models.configuracion import Setting
from app.models.conductores import Driver
from app.models.cotizaciones import Quotation
from app.models.cotizacion_items import QuotationItem  # noqa: F401 - register mapper
from app.models.cargas import Load
from app.models.clientes import Client
from app.models.documentos import Document
from app.models.gastos import Expense
from app.models.mantenimiento import Maintenance
from app.models.pagos import Payment
from app.models.retornos import ReturnBalanceCut, ReturnRecord  # noqa: F401 - register cut mapper
from app.models.retorno_desgloses import ReturnAllocation  # noqa: F401 - register mapper
from app.models.rutas import Route
from app.models.usuarios import User
from app.models.vehiculos import Vehicle
from app.models.viajes import Trip

MODEL_BY_MODULE = {
    "usuarios": User,
    "clientes": Client,
    "conductores": Driver,
    "vehiculos": Vehicle,
    "rutas": Route,
    "cargas": Load,
    "viajes": Trip,
    "cotizaciones": Quotation,
    "retornos": ReturnRecord,
    "documentos": Document,
    "gastos": Expense,
    "combustible": Fueling,
    "mantenimiento": Maintenance,
    "pagos": Payment,
    "configuracion": Setting,
}
