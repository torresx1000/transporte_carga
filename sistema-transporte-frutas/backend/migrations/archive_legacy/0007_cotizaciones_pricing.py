"""Add structured quote dates, route description, currency and rate fields.

Revision ID: 0007_cotizaciones_pricing
Revises: 0006_viajes_multi_load_route

Draft for Lote 2 Paso A. It has not been applied.
"""
from datetime import date
from decimal import Decimal
import json

import sqlalchemy as sa
from alembic import op

revision = "0007_cotizaciones_pricing"
down_revision = "0006_viajes_multi_load_route"
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
        raise RuntimeError(f"Invalid legacy quotation date: {value!r}") from None


def _basis_points(value, field):
    if value is None:
        return 0
    bps = Decimal(str(value).replace("%", "").strip().replace(",", ".")) * 100
    if bps != bps.to_integral_value() or bps < 0 or bps > 10000:
        raise RuntimeError(f"Legacy quotation {field} must be 0..100 percent with at most two decimals")
    return int(bps)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, data FROM cotizaciones ORDER BY created_at, id")).mappings().all()
    prepared = []
    for row in rows:
        data = _data(row["data"])
        currency = str(_get(data, "currency", "moneda") or "PEN").strip().upper()
        if currency != "PEN":
            raise RuntimeError("Quotation legacy row contains a currency outside the approved PEN-only list")
        client_id = _get(data, "client_id", "cliente_id")
        if client_id and conn.execute(sa.text("SELECT 1 FROM clientes WHERE id=:id"), {"id": client_id}).first() is None:
            raise RuntimeError(f"Quotation {row['id']} references a missing client")
        route_id = _get(data, "route_id", "ruta_id")
        if route_id and conn.execute(sa.text("SELECT 1 FROM rutas WHERE id=:id"), {"id": route_id}).first() is None:
            raise RuntimeError(f"Quotation {row['id']} references a missing route")
        prepared.append({
            "id": row["id"], "client_id": client_id, "route_id": route_id,
            "issue_date": _date(_get(data, "issue_date", "fecha_emision", "fecha")),
            "valid_until": _date(_get(data, "valid_until", "vigencia", "fecha_vencimiento")),
            "origin": _get(data, "origin", "origen"), "destination": _get(data, "destination", "destino"),
            "discount_rate_bps": _basis_points(_get(data, "discount_rate_bps", "descuento_porcentaje", "discount_percent"), "discount"),
            "tax_rate_bps": _basis_points(_get(data, "tax_rate_bps", "impuesto_porcentaje", "tax_percent"), "tax rate"),
        })
    op.add_column("cotizaciones", sa.Column("issue_date", sa.Date(), nullable=True))
    op.add_column("cotizaciones", sa.Column("valid_until", sa.Date(), nullable=True))
    op.add_column("cotizaciones", sa.Column("route_id", sa.String(36), nullable=True))
    op.add_column("cotizaciones", sa.Column("origin", sa.String(255), nullable=True))
    op.add_column("cotizaciones", sa.Column("destination", sa.String(255), nullable=True))
    op.add_column("cotizaciones", sa.Column("discount_rate_bps", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("cotizaciones", sa.Column("discount_minor", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("cotizaciones", sa.Column("tax_rate_bps", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("cotizaciones", sa.Column("currency", sa.String(3), nullable=False, server_default="PEN"))
    op.create_index("ix_cotizaciones_issue_date", "cotizaciones", ["issue_date"])
    op.create_index("ix_cotizaciones_valid_until", "cotizaciones", ["valid_until"])
    op.create_index("ix_cotizaciones_route_id", "cotizaciones", ["route_id"])
    op.create_foreign_key("fk_cotizaciones_route_id_rutas", "cotizaciones", "rutas", ["route_id"], ["id"])
    for row in prepared:
        conn.execute(sa.text(
            "UPDATE cotizaciones SET client_id=COALESCE(client_id,:client_id), route_id=:route_id, issue_date=:issue_date, "
            "valid_until=:valid_until, origin=:origin, destination=:destination, "
            "discount_rate_bps=:discount_rate_bps, tax_rate_bps=:tax_rate_bps, currency='PEN' WHERE id=:id"
        ), row)


def downgrade() -> None:
    conn = op.get_bind()
    table = sa.table(
        "cotizaciones", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
        sa.column("issue_date", sa.Date()), sa.column("valid_until", sa.Date()), sa.column("route_id", sa.String(36)),
        sa.column("origin", sa.String(255)), sa.column("destination", sa.String(255)),
        sa.column("discount_rate_bps", sa.Integer()), sa.column("discount_minor", sa.BigInteger()),
        sa.column("tax_rate_bps", sa.Integer()), sa.column("currency", sa.String(3)),
    )
    for row in conn.execute(sa.select(table)).mappings():
        data = _data(row["data"]).copy()
        values = {
            "fecha_emision": row["issue_date"].isoformat() if row["issue_date"] else None,
            "vigencia": row["valid_until"].isoformat() if row["valid_until"] else None,
            "ruta_id": row["route_id"],
            "origen": row["origin"], "destino": row["destination"],
            "descuento_porcentaje": row["discount_rate_bps"] / 100,
            "descuento_minor": row["discount_minor"], "impuesto_porcentaje": row["tax_rate_bps"] / 100,
            "moneda": row["currency"],
        }
        data.update({key: value for key, value in values.items() if value is not None})
        conn.execute(sa.update(table).where(table.c.id == row["id"]).values(data=data))
    op.drop_constraint("fk_cotizaciones_route_id_rutas", "cotizaciones", type_="foreignkey")
    op.drop_index("ix_cotizaciones_route_id", table_name="cotizaciones")
    op.drop_index("ix_cotizaciones_valid_until", table_name="cotizaciones")
    op.drop_index("ix_cotizaciones_issue_date", table_name="cotizaciones")
    for name in ("currency", "tax_rate_bps", "discount_minor", "discount_rate_bps",
                 "destination", "origin", "route_id", "valid_until", "issue_date"):
        op.drop_column("cotizaciones", name)
