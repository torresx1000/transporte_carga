from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.errors import register_error_handlers
from app.models import entities  # noqa: F401 - register mappings for Alembic
from app.schemas.responses import ErrorResponse

app = FastAPI(
    title="Sistema de Gestión de Cargas y Retornos",
    version="1.0.0",
    responses={
        status: {"model": ErrorResponse, "description": description}
        for status, description in {
            400: "Solicitud incorrecta",
            401: "Autenticación requerida o inválida",
            403: "Permisos insuficientes",
            404: "Recurso no encontrado",
            422: "Error de validación",
            500: "Error interno del servidor",
        }.items()
    },
)
register_error_handlers(app)
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/", tags=["sistema"])
def root():
    return {"mensaje": "API del Sistema de Gestión de Cargas y Retornos"}


@app.get("/health", tags=["sistema"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"api": "ok", "database": "connected"}
    except Exception:
        return {"api": "ok", "database": "disconnected"}
