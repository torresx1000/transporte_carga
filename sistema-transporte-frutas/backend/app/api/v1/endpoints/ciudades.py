from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_roles
from app.core.errors import ApiError
from app.models.rutas.rutas import City

router = APIRouter(prefix="/ciudades", tags=["ciudades"])
access = require_roles("admin", "operador")


class CiudadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nombre: str = Field(min_length=1, max_length=100)
    departamento: str | None = Field(default=None, max_length=100)
    provincia: str | None = Field(default=None, max_length=100)
    distrito: str | None = Field(default=None, max_length=100)


class CiudadResponse(CiudadCreate):
    id_ciudad: int
    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[CiudadResponse])
def cities(db: Session = Depends(get_db), user=Depends(access)):
    return list(db.scalars(select(City).order_by(City.nombre)).all())


@router.post("", response_model=CiudadResponse, status_code=201)
def create_city(payload: CiudadCreate, db: Session = Depends(get_db), user=Depends(access)):
    existing = db.scalar(select(City).where(func.lower(City.nombre) == payload.nombre.lower()))
    if existing:
        raise ApiError(409, "CITY_DUPLICATE", "La ciudad ya está registrada")
    item = City(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "CITY_DUPLICATE", "La ciudad ya está registrada") from exc
    return item
