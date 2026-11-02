"""Link fuel records to the trip they support."""

from alembic import op
import sqlalchemy as sa


revision = "0005_combustible_viaje"
down_revision = "0004_vehiculos_remolque"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("combustible", sa.Column("trip_id", sa.String(length=36), nullable=True))
    op.create_index("ix_combustible_trip_id", "combustible", ["trip_id"], unique=False)
    op.create_foreign_key(
        "fk_combustible_trip_id_viajes", "combustible", "viajes", ["trip_id"], ["id"]
    )


def downgrade():
    op.drop_constraint("fk_combustible_trip_id_viajes", "combustible", type_="foreignkey")
    op.drop_index("ix_combustible_trip_id", table_name="combustible")
    op.drop_column("combustible", "trip_id")
