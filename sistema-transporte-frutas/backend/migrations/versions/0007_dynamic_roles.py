"""Add persistent roles, dynamic permissions, and permission audit history."""

from alembic import op
import sqlalchemy as sa


revision = "0007_dynamic_roles"
down_revision = "0006_retorno_cortes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles_acceso",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_acceso_slug", "roles_acceso", ["slug"], unique=True)
    op.create_table(
        "roles_acceso_auditoria",
        sa.Column("role_id", sa.String(length=36), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles_acceso.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_acceso_auditoria_role_id", "roles_acceso_auditoria", ["role_id"])
    with op.batch_alter_table("usuarios") as batch:
        batch.add_column(sa.Column("permission_role_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_usuarios_permission_role_id",
            "roles_acceso",
            ["permission_role_id"],
            ["id"],
        )
        batch.create_index("ix_usuarios_permission_role_id", ["permission_role_id"])


def downgrade():
    with op.batch_alter_table("usuarios") as batch:
        batch.drop_index("ix_usuarios_permission_role_id")
        batch.drop_constraint("fk_usuarios_permission_role_id", type_="foreignkey")
        batch.drop_column("permission_role_id")
    op.drop_index("ix_roles_acceso_auditoria_role_id", table_name="roles_acceso_auditoria")
    op.drop_table("roles_acceso_auditoria")
    op.drop_index("ix_roles_acceso_slug", table_name="roles_acceso")
    op.drop_table("roles_acceso")
