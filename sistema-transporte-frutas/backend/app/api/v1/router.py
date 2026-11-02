from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    ciudades,
    portal,
    reportes,
    clientes,
    conductores,
    vehiculos,
    rutas,
    cargas,
    viajes,
    cotizaciones,
    retornos,
    documentos,
    gastos,
    combustible,
    mantenimiento,
    pagos,
    configuracion,
)
from app.api.v1.endpoints.usuarios import usuarios

router = APIRouter()

for endpoint_router in (
    auth.router,
    ciudades.router,
    usuarios.router,
    portal.router,
    reportes.router,
    clientes.router,
    conductores.router,
    vehiculos.router,
    rutas.router,
    cargas.router,
    viajes.router,
    cotizaciones.router,
    retornos.router,
    documentos.router,
    gastos.router,
    combustible.router,
    mantenimiento.router,
    pagos.router,
    configuracion.router,
):
    router.include_router(endpoint_router)
