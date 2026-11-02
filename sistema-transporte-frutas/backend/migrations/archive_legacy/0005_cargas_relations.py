"""Add structured load data and the trip assignment reference.

Revision ID: 0005_cargas_relations
Revises: 0004_rutas_fields

Draft for Lote 2 Paso A. It has not been applied.
"""
from datetime import date
from decimal import Decimal
import json

import sqlalchemy as sa
from alembic import op

revision = "0005_cargas_relations"
down_revision = "0004_rutas_fields"
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


def _date(value):
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise RuntimeError(f"Invalid legacy load date: {value!r}") from None


def _minor(data, minor_keys, major_keys):
    value = _get(data, *minor_keys)
    if value is not None:
        number = Decimal(str(value))
        if number != number.to_integral_value():
            raise RuntimeError("Legacy load amount in minor units must be an integer")
        return int(number)
    value = _get(data, *major_keys)
    if value is None:
        return None
    amount = Decimal(str(value).replace(",", ".")) * 100
    if amount != amount.to_integral_value():
        raise RuntimeError("Legacy load amount has more than two decimal places")
    return int(amount)


def _weights(data):
    quantity = _get(data, "quantity", "cantidad")
    unit = str(_get(data, "unit", "unidad_peso", "unidad") or "").strip().lower()
    net_total = _get(data, "net_weight_total_kg", "peso_neto_total_kg")
    if net_total is None:
        net_unit = _get(data, "net_weight_per_unit_kg", "peso_por_jaba_kg", "peso_unitario_kg")
        # The legacy form stored the 25 kg per-jaba value under peso_neto_kg.
        if net_unit is None and "jaba" in unit:
            net_unit = _get(data, "peso_neto_kg", "peso_neto")
        if net_unit is not None and quantity is not None and "jaba" in unit:
            net_total = Decimal(str(net_unit)) * Decimal(str(quantity))
        elif net_unit is not None and quantity is not None and data.get("weight_is_per_unit"):
            net_total = Decimal(str(net_unit)) * Decimal(str(quantity))
        else:
            net_total = _get(data, "net_weight_kg", "peso_neto_kg", "peso_neto")
    gross_total = _get(data, "gross_weight_total_kg", "peso_bruto_total_kg", "gross_weight_kg", "peso_bruto_kg", "peso_bruto")
    return net_total, gross_total


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, data FROM cargas ORDER BY created_at, id")).mappings().all()
    prepared = []
    for row in rows:
        data = _data(row["data"])
        currency = str(_get(data, "currency", "moneda") or "PEN").strip().upper()
        if currency != "PEN":
            raise RuntimeError("Carga legacy contains a currency outside the approved PEN-only list")
        trip_id = _get(data, "trip_id", "viaje_id")
        net_weight, gross_weight = _weights(data)
        prepared.append({
            "id": row["id"],
            "client_id": _get(data, "client_id", "cliente_id"),
            "trip_id": trip_id,
            "product": _get(data, "product", "producto", "fruta"),
            "variety": _get(data, "variety", "variedad"),
            "quantity": _get(data, "quantity", "cantidad"),
            "unit": _get(data, "unit", "unidad_peso", "unidad"),
            "net_weight_kg": net_weight,
            "gross_weight_kg": gross_weight,
            "origin": _get(data, "origin", "procedencia", "origen"),
            "destination": _get(data, "destination", "destino"),
            "pickup_date": _date(_get(data, "pickup_date", "fecha_recojo")),
            "delivery_date": _date(_get(data, "delivery_date", "fecha_entrega")),
            "charge_amount_minor": _minor(data, ("charge_amount_minor", "monto_cobrar_minor"),
                                           ("charge_amount", "monto_a_cobrar")),
        })
    for row in prepared:
        if row["trip_id"] and conn.execute(sa.text("SELECT 1 FROM viajes WHERE id=:id"), {"id": row["trip_id"]}).first() is None:
            raise RuntimeError(f"Load {row['id']} references a missing trip")
        if row["client_id"] and conn.execute(sa.text("SELECT 1 FROM clientes WHERE id=:id"), {"id": row["client_id"]}).first() is None:
            raise RuntimeError(f"Load {row['id']} references a missing client")

    op.add_column("cargas", sa.Column("trip_id", sa.String(36), nullable=True))
    op.add_column("cargas", sa.Column("product", sa.String(100), nullable=True))
    op.add_column("cargas", sa.Column("variety", sa.String(100), nullable=True))
    op.add_column("cargas", sa.Column("quantity", sa.Integer(), nullable=True))
    op.add_column("cargas", sa.Column("unit", sa.String(30), nullable=True))
    op.add_column("cargas", sa.Column("net_weight_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("cargas", sa.Column("gross_weight_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("cargas", sa.Column("origin", sa.String(255), nullable=True))
    op.add_column("cargas", sa.Column("destination", sa.String(255), nullable=True))
    op.add_column("cargas", sa.Column("pickup_date", sa.Date(), nullable=True))
    op.add_column("cargas", sa.Column("delivery_date", sa.Date(), nullable=True))
    op.add_column("cargas", sa.Column("charge_amount_minor", sa.BigInteger(), nullable=True))
    op.add_column("cargas", sa.Column("currency", sa.String(3), nullable=False, server_default="PEN"))
    op.create_index("ix_cargas_trip_id", "cargas", ["trip_id"])
    op.create_index("ix_cargas_product", "cargas", ["product"])
    op.create_foreign_key("fk_cargas_trip_id_viajes", "cargas", "viajes", ["trip_id"], ["id"])

    for row in prepared:
        conn.execute(sa.text(
            "UPDATE cargas SET client_id=COALESCE(client_id,:client_id), trip_id=:trip_id, "
            "product=:product, variety=:variety, quantity=:quantity, unit=:unit, "
            "net_weight_kg=:net_weight_kg, gross_weight_kg=:gross_weight_kg, "
            "origin=:origin, destination=:destination, pickup_date=:pickup_date, "
            "delivery_date=:delivery_date, charge_amount_minor=:charge_amount_minor, currency='PEN' "
            "WHERE id=:id"
        ), row)


def downgrade() -> None:
    conn = op.get_bind()
    table = sa.table(
        "cargas", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
        sa.column("trip_id", sa.String(36)), sa.column("product", sa.String(100)),
        sa.column("variety", sa.String(100)), sa.column("quantity", sa.Integer()),
        sa.column("unit", sa.String(30)), sa.column("net_weight_kg", sa.Numeric(12, 3)),
        sa.column("gross_weight_kg", sa.Numeric(12, 3)), sa.column("origin", sa.String(255)),
        sa.column("destination", sa.String(255)), sa.column("pickup_date", sa.Date()),
        sa.column("delivery_date", sa.Date()), sa.column("charge_amount_minor", sa.BigInteger()),
        sa.column("currency", sa.String(3)),
    )
    for row in conn.execute(sa.select(table)).mappings():
        data = _data(row["data"]).copy()
        values = {
            "viaje_id": row["trip_id"], "fruta": row["product"], "variedad": row["variety"],
            "cantidad": row["quantity"], "unidad_peso": row["unit"],
            # Keep legacy peso_neto_kg/peso_bruto_kg values intact; these keys
            # hold the normalized totals written back by this schema.
            "peso_neto_total_kg": float(row["net_weight_kg"]) if row["net_weight_kg"] is not None else None,
            "peso_bruto_total_kg": float(row["gross_weight_kg"]) if row["gross_weight_kg"] is not None else None,
            "procedencia": row["origin"], "destino": row["destination"],
            "fecha_recojo": row["pickup_date"].isoformat() if row["pickup_date"] else None,
            "fecha_entrega": row["delivery_date"].isoformat() if row["delivery_date"] else None,
            "monto_cobrar_minor": row["charge_amount_minor"], "moneda": row["currency"],
        }
        data.update({key: value for key, value in values.items() if value is not None})
        conn.execute(sa.update(table).where(table.c.id == row["id"]).values(data=data))
    op.drop_constraint("fk_cargas_trip_id_viajes", "cargas", type_="foreignkey")
    op.drop_index("ix_cargas_product", table_name="cargas")
    op.drop_index("ix_cargas_trip_id", table_name="cargas")
    for name in ("currency", "charge_amount_minor", "delivery_date", "pickup_date", "destination",
                 "origin", "gross_weight_kg", "net_weight_kg", "unit", "quantity", "variety", "product", "trip_id"):
        op.drop_column("cargas", name)
