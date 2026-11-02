"""Store whether each vehicle has a trailer and its plate."""

from alembic import op
import sqlalchemy as sa

revision = "0004_vehiculos_remolque"
down_revision = "0003_carga_etapas"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehiculos", sa.Column("has_trailer", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("vehiculos", sa.Column("trailer_plate", sa.String(length=20), nullable=True))
    op.alter_column("vehiculos", "has_trailer", server_default=None)


def downgrade():
    op.drop_column("vehiculos", "trailer_plate")
    op.drop_column("vehiculos", "has_trailer")
