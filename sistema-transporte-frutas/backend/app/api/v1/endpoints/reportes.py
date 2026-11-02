from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.api.v1.endpoints.retornos.retornos import return_balances
from app.models.entities import MODEL_BY_MODULE, Client, Expense, Fueling, Load, ReturnRecord, Trip, User, Vehicle
from app.schemas.responses import (
    DashboardReportResponse,
    FuelConsumptionResponse,
    TripProfitabilityResponse,
)

router = APIRouter(prefix="/reportes", tags=["reportes"])
admin_or_operator = require_roles("admin", "operador")


@router.get("/dashboard", response_model=DashboardReportResponse)
def dashboard_report(db: Session = Depends(get_db), user: User = Depends(admin_or_operator)):
    def count(model, condition=None):
        query = select(func.count()).select_from(model).where(model.deleted_at.is_(None))
        if condition is not None:
            query = query.where(condition)
        return db.scalar(query) or 0

    return {
        "clientes": count(Client),
        "cargas": count(Load),
        "cargas_en_transito": count(Load, Load.status == "en_transito"),
        "viajes": count(MODEL_BY_MODULE["viajes"]),
        "retornos": count(ReturnRecord),
    }


@router.get("/rentabilidad-viaje/{trip_id}", response_model=TripProfitabilityResponse)
def trip_profitability(
    trip_id: str, db: Session = Depends(get_db), user: User = Depends(admin_or_operator)
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.deleted_at:
        raise HTTPException(404, "Viaje no encontrado")
    costs = (
        db.scalar(
            select(func.sum(Expense.amount)).where(
                Expense.trip_id == trip_id, Expense.deleted_at.is_(None)
            )
        )
        or 0
    )
    fuel_costs = (
        db.scalar(
            select(func.sum(Fueling.price_cents)).where(
                Fueling.trip_id == trip_id, Fueling.deleted_at.is_(None)
            )
        )
        or 0
    )
    costs += fuel_costs
    revenue = int(trip.data.get("ingreso_centimos", 0))
    return {
        "viaje_id": trip_id,
        "ingresos_centimos": revenue,
        "costos_centimos": costs,
        "utilidad_centimos": revenue - costs,
    }


@router.get("/consumo-combustible", response_model=list[FuelConsumptionResponse])
def fuel_consumption(db: Session = Depends(get_db), user: User = Depends(admin_or_operator)):
    rows = db.execute(
        select(Fueling.vehicle_id, func.sum(Fueling.liters_milli), func.sum(Fueling.price_cents))
        .where(Fueling.deleted_at.is_(None))
        .group_by(Fueling.vehicle_id)
    ).all()
    return [
        {"vehiculo_id": vehicle_id, "litros": liters / 1000, "costo_centimos": cost}
        for vehicle_id, liters, cost in rows
    ]


@router.get("/costos-vehiculo/{vehicle_id}")
def vehicle_cost_report(
    vehicle_id: str, db: Session = Depends(get_db), user: User = Depends(admin_or_operator)
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.deleted_at:
        raise HTTPException(404, "Vehículo no encontrado")

    expenses = db.scalars(
        select(Expense)
        .outerjoin(Trip, Expense.trip_id == Trip.id)
        .where(
            Expense.deleted_at.is_(None),
            or_(Expense.vehicle_id == vehicle_id, Trip.vehicle_id == vehicle_id),
        )
    ).all()
    trips_by_id = {
        trip.id: trip
        for trip in db.scalars(
            select(Trip).where(Trip.vehicle_id == vehicle_id, Trip.deleted_at.is_(None))
        ).all()
    }
    items = []
    for expense in expenses:
        data = expense.data or {}
        trip = trips_by_id.get(expense.trip_id)
        items.append(
            {
                "id": expense.id,
                "tipo": "gasto",
                "fecha": expense.created_at.isoformat() if expense.created_at else None,
                "viaje_id": expense.trip_id,
                "viaje_codigo": trip.code if trip else None,
                "concepto": expense.category,
                "detalle": data.get("detalle") or data.get("descripcion"),
                "monto_centimos": expense.amount,
            }
        )

    fuelings = db.scalars(
        select(Fueling)
        .outerjoin(Trip, Fueling.trip_id == Trip.id)
        .where(
            Fueling.deleted_at.is_(None),
            or_(Fueling.vehicle_id == vehicle_id, Trip.vehicle_id == vehicle_id),
        )
    ).all()
    for fueling in fuelings:
        data = fueling.data or {}
        trip = trips_by_id.get(fueling.trip_id)
        items.append(
            {
                "id": fueling.id,
                "tipo": "combustible",
                "fecha": data.get("fecha_consumo")
                or (fueling.created_at.isoformat() if fueling.created_at else None),
                "viaje_id": fueling.trip_id,
                "viaje_codigo": trip.code if trip else None,
                "concepto": "Abastecimiento de combustible",
                "detalle": f"{fueling.liters_milli / 1000:g} L · odómetro {fueling.odometer} km",
                "litros_milesimas": fueling.liters_milli,
                "monto_centimos": fueling.price_cents,
            }
        )

    items.sort(key=lambda row: row["fecha"] or "", reverse=True)
    return {
        "vehiculo_id": vehicle.id,
        "placa": vehicle.plate,
        "total_centimos": sum(item["monto_centimos"] for item in items),
        "cantidad_registros": len(items),
        "items": items,
    }


@router.get("/jabas-pendientes")
def crate_balances(db: Session = Depends(get_db), user: User = Depends(admin_or_operator)):
    return return_balances(db, user)
