"""Add structured route code, operating values, and integer minor-unit amounts.

Revision ID: 0004_rutas_fields
Revises: 0003_vehiculos_fields
"""
from decimal import Decimal, InvalidOperation
import json
import re

import sqlalchemy as sa
from alembic import op

revision = "0004_rutas_fields"
down_revision = "0003_vehiculos_fields"
branch_labels = None
depends_on = None

_CODE = re.compile(r"^R-(\d{3})$", re.IGNORECASE)
_DURATION = re.compile(r"^\s*(?:(\d+(?:[.,]\d+)?)\s*h(?:oras?)?)?\s*(?:(\d+(?:[.,]\d+)?)\s*m(?:in(?:utos?)?)?)?\s*$", re.IGNORECASE)


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
        raw = _first(data, "code", "codigo", "route_code")
        match = _CODE.fullmatch(str(raw).strip()) if raw else None
        code = f"R-{int(match.group(1)):03d}" if match else None
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
            raise RuntimeError("More than 999 route codes are needed; R-NNN format is exhausted")
        code = f"R-{next_number:03d}"
        result[row["id"]] = code
        reserved.add(next_number)
        next_number += 1
    return result


def _distance(value):
    if value is None:
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise RuntimeError(f"Invalid legacy route distance: {value!r}") from None


def _money_minor(data, minor_keys, major_keys):
    value = _first(data, *minor_keys)
    if value is not None:
        try:
            number = Decimal(str(value).strip().replace(",", "."))
        except (InvalidOperation, ValueError):
            raise RuntimeError("Invalid legacy route amount in minor units") from None
        if number != number.to_integral_value():
            raise RuntimeError("Legacy route amount in minor units must be an integer")
        return int(number)
    value = _first(data, *major_keys)
    if value is None:
        return None
    try:
        minor = Decimal(str(value).strip().replace(",", ".")) * 100
    except (InvalidOperation, ValueError):
        raise RuntimeError("Invalid legacy PEN route amount") from None
    if minor != minor.to_integral_value():
        raise RuntimeError("Legacy PEN route amount has more than two decimal places")
    return int(minor)


def _duration(data):
    explicit_minutes = _first(data, "estimated_duration_minutes", "duracion_minutos")
    if explicit_minutes is not None:
        try:
            return int(explicit_minutes)
        except (TypeError, ValueError):
            raise RuntimeError(f"Invalid legacy route duration in minutes: {explicit_minutes!r}") from None
    value = _first(data, "estimated_duration", "duration", "duracion_estimada", "duracion")
    if value is None:
        return None
    match = _DURATION.fullmatch(str(value))
    if not match or not any(match.groups()):
        raise RuntimeError(f"Unrecognized legacy route duration format: {value!r}")
    hours = Decimal((match.group(1) or "0").replace(",", "."))
    minutes = Decimal((match.group(2) or "0").replace(",", "."))
    total = hours * 60 + minutes
    if total != total.to_integral_value():
        raise RuntimeError(f"Legacy route duration does not resolve to whole minutes: {value!r}")
    return int(total)


def _status(data):
    value = _first(data, "status", "estado")
    if value is None:
        return None
    normalized = str(value).strip().lower()
    mapping = {"activo": "activa", "active": "activa", "activa": "activa",
               "inactivo": "inactiva", "inactive": "inactiva", "inactiva": "inactiva"}
    return mapping.get(normalized, normalized)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, created_at, data FROM rutas ORDER BY created_at, id"
    )).mappings().all()
    codes = _codes(rows)
    prepared = []
    for row in rows:
        data = _data(row["data"])
        # PEN is the approved default. Preserve an explicitly stored currency;
        # otherwise backfill PEN so every existing route has a currency.
        currency = _first(data, "currency", "moneda")
        currency = str(currency).strip().upper() if currency else "PEN"
        if currency != "PEN":
            raise RuntimeError(f"Route {row['id']} has a legacy currency outside the approved PEN-only list")
        prepared.append((row["id"], codes[row["id"]], _status(data),
                         _distance(_first(data, "distance_km", "distancia_km", "distance", "distancia")),
                         _duration(data),
                         _money_minor(data, ("tolls_minor", "peajes_minor"), ("peajes", "tolls")),
                         _money_minor(data, ("reference_tariff_minor", "tarifa_referencial_minor"),
                                      ("tarifa_referencial", "reference_tariff", "referencePrice")),
                         currency))

    op.add_column("rutas", sa.Column("code", sa.String(length=10), nullable=True))
    op.add_column("rutas", sa.Column("status", sa.String(length=30), nullable=True))
    op.add_column("rutas", sa.Column("distance_km", sa.Numeric(precision=12, scale=3), nullable=True))
    op.add_column("rutas", sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True))
    op.add_column("rutas", sa.Column("tolls_minor", sa.BigInteger(), nullable=True))
    op.add_column("rutas", sa.Column("reference_tariff_minor", sa.BigInteger(), nullable=True))
    op.add_column("rutas", sa.Column("currency", sa.String(length=3), nullable=True))
    op.create_unique_constraint("uq_rutas_code", "rutas", ["code"])
    for route_id, code, status, distance, duration, tolls, tariff, currency in prepared:
        conn.execute(sa.text(
            "UPDATE rutas SET code=:code, status=:status, distance_km=:distance, "
            "estimated_duration_minutes=:duration, tolls_minor=:tolls, "
            "reference_tariff_minor=:tariff, currency=:currency WHERE id=:id"
        ), {"code": code, "status": status, "distance": distance,
            "duration": duration, "tolls": tolls, "tariff": tariff,
            "currency": currency, "id": route_id})


def downgrade() -> None:
    conn = op.get_bind()
    table = sa.table(
        "rutas", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
        sa.column("code", sa.String(10)), sa.column("status", sa.String(30)),
        sa.column("distance_km", sa.Numeric(12, 3)), sa.column("estimated_duration_minutes", sa.Integer()),
        sa.column("tolls_minor", sa.BigInteger()), sa.column("reference_tariff_minor", sa.BigInteger()),
        sa.column("currency", sa.String(3)),
    )
    rows = conn.execute(sa.select(table)).mappings().all()
    for row in rows:
        data = _data(row["data"]).copy()
        values = {
            "code": row["code"], "status": row["status"],
            "distance_km": float(row["distance_km"]) if row["distance_km"] is not None else None,
            "estimated_duration_minutes": row["estimated_duration_minutes"],
            "tolls_minor": row["tolls_minor"], "reference_tariff_minor": row["reference_tariff_minor"],
            "currency": row["currency"],
        }
        data.update({key: value for key, value in values.items() if value is not None})
        conn.execute(sa.update(table).where(table.c.id == row["id"]).values(data=data))
    op.drop_constraint("uq_rutas_code", "rutas", type_="unique")
    op.drop_column("rutas", "currency")
    op.drop_column("rutas", "reference_tariff_minor")
    op.drop_column("rutas", "tolls_minor")
    op.drop_column("rutas", "estimated_duration_minutes")
    op.drop_column("rutas", "distance_km")
    op.drop_column("rutas", "status")
    op.drop_column("rutas", "code")
