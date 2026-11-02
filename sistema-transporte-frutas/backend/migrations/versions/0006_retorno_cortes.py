"""Add auditable per-client crate balance cuts."""

from alembic import op
import sqlalchemy as sa


revision = "0006_retorno_cortes"
down_revision = "0005_combustible_viaje"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "retorno_historial_cortes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("dispatched_total", sa.Integer(), nullable=False),
        sa.Column("returned_total", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clientes.id"]),
        sa.UniqueConstraint(
            "client_id", "sequence", name="uq_retorno_historial_cliente_sequence"
        ),
    )
    op.create_index(
        "ix_retorno_historial_cortes_client_id",
        "retorno_historial_cortes",
        ["client_id"],
    )

    for table in ("cargas", "retornos", "retorno_desgloses"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("balance_period_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_balance_period_id_retorno_historial_cortes",
                "retorno_historial_cortes",
                ["balance_period_id"],
                ["id"],
            )
            batch.create_index(f"ix_{table}_balance_period_id", ["balance_period_id"])


def downgrade():
    for table in ("retorno_desgloses", "retornos", "cargas"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_balance_period_id")
            batch.drop_constraint(
                f"fk_{table}_balance_period_id_retorno_historial_cortes",
                type_="foreignkey",
            )
            batch.drop_column("balance_period_id")
    op.drop_index(
        "ix_retorno_historial_cortes_client_id",
        table_name="retorno_historial_cortes",
    )
    op.drop_table("retorno_historial_cortes")
