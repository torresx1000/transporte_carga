"""Add structured vehicle fleet code and operational fields.

Revision ID: 0003_vehiculos_fields
Revises: 0002_conductores_fields
"""
import json
import re

import sqlalchemy as sa
from alembic import op

revision = "0003_vehiculos_fields"
down_revision = "0002_conductores_fields"
branch_labels = None
depends_on = None

_CODE = re.compile(r"^V-(\d{2,3})$", re.IGNORECASE)


def _data(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return {}
    return value if isinstance(value, dict) else {}


def _first(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def _codes(rows):
    legacy = {}
    counts = {}
    reserved = set()
    for row in rows:
        data = _data(row["data"])
        raw = _first(data, "fleet_code", "codigo_flota", "codigo", "code")
        match = _CODE.fullmatch(str(raw).strip()) if raw else None
        code = f"V-{int(match.group(1)):02d}" if match else None
        legacy[row["id"]] = code
        if code:
            counts[code] = counts.get(code, 0) + 1
            reserved.add(int(code[2:]))
    result = {}
    for row in rows:
        code = legacy[row["id"]]
        if code and counts[code] == 1:
            result[row["id"]] = code
    next_number = 1
    for row in rows:
        if row["id"] in result:
            continue
        while next_number in reserved:
            next_number += 1
        if next_number > 999:
            raise RuntimeError("More than 999 fleet codes are needed; V-NNN format is exhausted")
        code = f"V-{next_number:02d}"
        result[row["id"]] = code
        reserved.add(next_number)
        next_number += 1
    return result


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, created_at, data FROM vehiculos ORDER BY created_at, id"
    )).mappings().all()
    codes = _codes(rows)
    prepared = []
    for row in rows:
        data = _data(row["data"])
        vehicle_type = _first(data, "vehicle_type", "tipo", "type", "categoria")
        capacity = _first(data, "capacity_kg", "capacidad_kg", "capacidad")
        try:
            capacity = int(float(capacity)) if capacity is not None else None
        except (TypeError, ValueError):
            raise RuntimeError(f"Invalid legacy vehicle capacity for record {row['id']}") from None
        prepared.append((row["id"], codes[row["id"]], vehicle_type, capacity))

    op.add_column("vehiculos", sa.Column("fleet_code", sa.String(length=10), nullable=True))
    op.add_column("vehiculos", sa.Column("vehicle_type", sa.String(length=30), nullable=True))
    op.add_column("vehiculos", sa.Column("capacity_kg", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_vehiculos_fleet_code", "vehiculos", ["fleet_code"])
    for vehicle_id, code, vehicle_type, capacity in prepared:
        conn.execute(sa.text(
            "UPDATE vehiculos SET fleet_code=:code, vehicle_type=:vehicle_type, capacity_kg=:capacity WHERE id=:id"
        ), {"code": code, "vehicle_type": str(vehicle_type).strip() if vehicle_type else None,
            "capacity": capacity, "id": vehicle_id})


def downgrade() -> None:
    conn = op.get_bind()
    table = sa.table(
        "vehiculos", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
        sa.column("fleet_code", sa.String(10)), sa.column("vehicle_type", sa.String(30)),
        sa.column("capacity_kg", sa.Integer()),
    )
    rows = conn.execute(sa.select(table)).mappings().all()
    for row in rows:
        data = _data(row["data"]).copy()
        values = {"fleet_code": row["fleet_code"], "vehicle_type": row["vehicle_type"],
                  "capacity_kg": row["capacity_kg"]}
        data.update({key: value for key, value in values.items() if value is not None})
        conn.execute(sa.update(table).where(table.c.id == row["id"]).values(data=data))
    op.drop_constraint("uq_vehiculos_fleet_code", "vehiculos", type_="unique")
    op.drop_column("vehiculos", "capacity_kg")
    op.drop_column("vehiculos", "vehicle_type")
    op.drop_column("vehiculos", "fleet_code")
