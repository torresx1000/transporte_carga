"""Add route and scheduling fields to trips and backfill load assignments.

Revision ID: 0006_viajes_multi_load_route
Revises: 0005_cargas_relations

Draft for Lote 2 Paso A. It has not been applied.
"""
from datetime import datetime
from decimal import Decimal
import json

import sqlalchemy as sa
from alembic import op

revision = "0006_viajes_multi_load_route"
down_revision = "0005_cargas_relations"
branch_labels = None
depends_on = None


def _data(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


def _get(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _datetime(value):
    if value is None:
        return None
    normalized = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.combine(datetime.fromisoformat(normalized[:10]).date(), datetime.min.time())
        except ValueError:
            raise RuntimeError(f"Invalid legacy trip date/time: {value!r}") from None


def _minor(data):
    value = _get(data, "freight_amount_minor", "monto_flete_minor", "flete_minor")
    if value is not None:
        number = Decimal(str(value))
        if number != number.to_integral_value():
            raise RuntimeError("Legacy freight in minor units must be an integer")
        return int(number)
    value = _get(data, "freight_amount", "monto_flete", "flete")
    if value is None:
        return None
    amount = Decimal(str(value).replace(",", ".")) * 100
    if amount != amount.to_integral_value():
        raise RuntimeError("Legacy freight has more than two decimal places")
    return int(amount)


def _load_ids(data, legacy_load_id):
    values = data.get("cargas") or data.get("load_ids") or data.get("carga_ids") or []
    if not isinstance(values, list):
        raise RuntimeError("Legacy trip loads must be a list of load IDs")
    if legacy_load_id:
        values = [legacy_load_id, *values]
    single = _get(data, "load_id", "carga_id")
    if single:
        values.append(single)
    result = []
    for value in values:
        load_id = value.get("id") if isinstance(value, dict) else value
        if load_id and str(load_id) not in result:
            result.append(str(load_id))
    return result


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, load_id, data FROM viajes ORDER BY created_at, id")).mappings().all()
    prepared = []
    assignment_owner = {}
    for row in rows:
        data = _data(row["data"])
        currency = str(_get(data, "currency", "moneda") or "PEN").strip().upper()
        if currency != "PEN":
            raise RuntimeError("Trip legacy row contains a currency outside the approved PEN-only list")
        route_id = _get(data, "route_id", "ruta_id")
        load_ids = _load_ids(data, row["load_id"])
        for load_id in load_ids:
            owner = assignment_owner.setdefault(load_id, row["id"])
            if owner != row["id"]:
                raise RuntimeError(f"Load {load_id} is assigned to more than one trip in legacy data")
            if conn.execute(sa.text("SELECT 1 FROM cargas WHERE id=:id"), {"id": load_id}).first() is None:
                raise RuntimeError(f"Trip {row['id']} references a missing load")
        if route_id and conn.execute(sa.text("SELECT 1 FROM rutas WHERE id=:id"), {"id": route_id}).first() is None:
            raise RuntimeError(f"Trip {row['id']} references a missing route")
        prepared.append({
            "id": row["id"], "route_id": route_id,
            "scheduled_start_at": _datetime(_get(data, "scheduled_start_at", "fecha_salida", "departure_at")),
            "scheduled_end_at": _datetime(_get(data, "scheduled_end_at", "fecha_entrega_estimada", "estimated_delivery_at")),
            "actual_start_at": _datetime(_get(data, "actual_start_at", "salida_real")),
            "actual_end_at": _datetime(_get(data, "actual_end_at", "entrega_real")),
            "freight_amount_minor": _minor(data), "load_ids": load_ids,
        })
    # Reject already-assigned loads only when they point to a different trip.
    for load_id, trip_id in assignment_owner.items():
        existing = conn.execute(sa.text("SELECT trip_id FROM cargas WHERE id=:id"), {"id": load_id}).scalar()
        if existing and existing != trip_id:
            raise RuntimeError(f"Load {load_id} is already linked to another trip")

    op.add_column("viajes", sa.Column("route_id", sa.String(36), nullable=True))
    op.add_column("viajes", sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("viajes", sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("viajes", sa.Column("actual_start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("viajes", sa.Column("actual_end_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("viajes", sa.Column("freight_amount_minor", sa.BigInteger(), nullable=True))
    op.add_column("viajes", sa.Column("currency", sa.String(3), nullable=False, server_default="PEN"))
    op.create_index("ix_viajes_route_id", "viajes", ["route_id"])
    op.create_index("ix_viajes_scheduled_start_at", "viajes", ["scheduled_start_at"])
    op.create_foreign_key("fk_viajes_route_id_rutas", "viajes", "rutas", ["route_id"], ["id"])
    for row in prepared:
        conn.execute(sa.text(
            "UPDATE viajes SET route_id=:route_id, scheduled_start_at=:scheduled_start_at, "
            "scheduled_end_at=:scheduled_end_at, actual_start_at=:actual_start_at, "
            "actual_end_at=:actual_end_at, freight_amount_minor=:freight_amount_minor, currency='PEN' "
            "WHERE id=:id"
        ), row)
        for load_id in row["load_ids"]:
            conn.execute(sa.text("UPDATE cargas SET trip_id=:trip_id WHERE id=:load_id AND trip_id IS NULL"),
                         {"trip_id": row["id"], "load_id": load_id})
    op.drop_constraint("viajes_ibfk_1", "viajes", type_="foreignkey")
    op.drop_index("ix_viajes_load_id", table_name="viajes")
    op.drop_column("viajes", "load_id")


def downgrade() -> None:
    conn = op.get_bind()
    table = sa.table(
        "viajes", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
        sa.column("route_id", sa.String(36)), sa.column("scheduled_start_at", sa.DateTime()),
        sa.column("scheduled_end_at", sa.DateTime()), sa.column("actual_start_at", sa.DateTime()),
        sa.column("actual_end_at", sa.DateTime()), sa.column("freight_amount_minor", sa.BigInteger()),
        sa.column("currency", sa.String(3)),
    )
    for row in conn.execute(sa.select(table)).mappings():
        data = _data(row["data"]).copy()
        values = {
            "ruta_id": row["route_id"], "fecha_salida": row["scheduled_start_at"].isoformat() if row["scheduled_start_at"] else None,
            "fecha_entrega_estimada": row["scheduled_end_at"].isoformat() if row["scheduled_end_at"] else None,
            "salida_real": row["actual_start_at"].isoformat() if row["actual_start_at"] else None,
            "entrega_real": row["actual_end_at"].isoformat() if row["actual_end_at"] else None,
            "monto_flete_minor": row["freight_amount_minor"], "moneda": row["currency"],
        }
        data.update({key: value for key, value in values.items() if value is not None})
        conn.execute(sa.update(table).where(table.c.id == row["id"]).values(data=data))
    # Recreate the legacy singular pointer only when it can represent the relation.
    # For multi-load trips, preserve every load ID in JSON and leave load_id NULL.
    loads = sa.table("cargas", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
                     sa.column("trip_id", sa.String(36)), sa.column("created_at", sa.DateTime()))
    op.add_column("viajes", sa.Column("load_id", sa.String(36), nullable=True))
    op.create_index("ix_viajes_load_id", "viajes", ["load_id"])
    op.create_foreign_key("fk_viajes_load_id_cargas", "viajes", "cargas", ["load_id"], ["id"])
    trip_ids = conn.execute(sa.text("SELECT id FROM viajes")).scalars().all()
    for trip_id in trip_ids:
        assigned = conn.execute(sa.select(loads.c.id).where(loads.c.trip_id == trip_id).order_by(loads.c.created_at, loads.c.id)).scalars().all()
        conn.execute(sa.text("UPDATE viajes SET load_id=:load_id WHERE id=:id"),
                     {"load_id": assigned[0] if len(assigned) == 1 else None, "id": trip_id})
        trip_data = conn.execute(sa.select(table.c.data).where(table.c.id == trip_id)).scalar()
        data = _data(trip_data).copy()
        if assigned:
            data["carga_ids"] = list(assigned)
        conn.execute(sa.update(table).where(table.c.id == trip_id).values(data=data))
    op.drop_constraint("fk_viajes_route_id_rutas", "viajes", type_="foreignkey")
    op.drop_index("ix_viajes_scheduled_start_at", table_name="viajes")
    op.drop_index("ix_viajes_route_id", table_name="viajes")
    for name in ("currency", "freight_amount_minor", "actual_end_at", "actual_start_at",
                 "scheduled_end_at", "scheduled_start_at", "route_id"):
        op.drop_column("viajes", name)
