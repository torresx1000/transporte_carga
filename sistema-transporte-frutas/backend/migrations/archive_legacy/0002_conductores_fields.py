"""Add structured driver license and document fields.

Revision ID: 0002_conductores_fields
Revises: 0001_initial_schema
"""
from datetime import date, datetime
import json

import sqlalchemy as sa
from alembic import op

revision = "0002_conductores_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


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


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized driver document date format: {raw!r}")


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, created_at, document, data FROM conductores ORDER BY created_at, id"
    )).mappings().all()

    prepared = []
    licenses = {}
    for row in rows:
        data = _data(row["data"])
        license_number = _first(data, "license_number", "licencia", "numero_licencia")
        if license_number:
            key = str(license_number).strip().upper()
            licenses.setdefault(key, []).append(row["id"])
        prepared.append((row["id"], license_number, _first(data, "license_category", "categoria_licencia", "categoria"),
                         _as_date(_first(data, "license_expires_at", "licencia_vence", "vencimiento_licencia")),
                         _as_date(_first(data, "medical_exam_expires_at", "examen_medico_vence", "vencimiento_examen_medico"))))
    duplicates = [key for key, ids in licenses.items() if len(ids) > 1]
    if duplicates:
        raise RuntimeError("Duplicate legacy driver license numbers prevent a unique backfill")

    op.add_column("conductores", sa.Column("license_number", sa.String(length=50), nullable=True))
    op.add_column("conductores", sa.Column("license_category", sa.String(length=30), nullable=True))
    op.add_column("conductores", sa.Column("license_expires_at", sa.Date(), nullable=True))
    op.add_column("conductores", sa.Column("medical_exam_expires_at", sa.Date(), nullable=True))
    op.create_unique_constraint("uq_conductores_license_number", "conductores", ["license_number"])
    for driver_id, license_number, category, license_expiry, medical_expiry in prepared:
        conn.execute(sa.text(
            "UPDATE conductores SET license_number=:license_number, license_category=:category, "
            "license_expires_at=:license_expiry, medical_exam_expires_at=:medical_expiry WHERE id=:id"
        ), {"license_number": str(license_number).strip() if license_number else None,
            "category": str(category).strip() if category else None,
            "license_expiry": license_expiry, "medical_expiry": medical_expiry, "id": driver_id})


def downgrade() -> None:
    conn = op.get_bind()
    table = sa.table(
        "conductores", sa.column("id", sa.String(36)), sa.column("data", sa.JSON()),
        sa.column("license_number", sa.String(50)), sa.column("license_category", sa.String(30)),
        sa.column("license_expires_at", sa.Date()), sa.column("medical_exam_expires_at", sa.Date()),
    )
    rows = conn.execute(sa.select(table)).mappings().all()
    for row in rows:
        data = _data(row["data"]).copy()
        values = {
            "license_number": row["license_number"],
            "license_category": row["license_category"],
            "license_expires_at": row["license_expires_at"].isoformat() if row["license_expires_at"] else None,
            "medical_exam_expires_at": row["medical_exam_expires_at"].isoformat() if row["medical_exam_expires_at"] else None,
        }
        data.update({key: value for key, value in values.items() if value is not None})
        conn.execute(sa.update(table).where(table.c.id == row["id"]).values(data=data))
    op.drop_constraint("uq_conductores_license_number", "conductores", type_="unique")
    op.drop_column("conductores", "medical_exam_expires_at")
    op.drop_column("conductores", "license_expires_at")
    op.drop_column("conductores", "license_category")
    op.drop_column("conductores", "license_number")
