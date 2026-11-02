"""One load, many ordered transport stages."""

from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = "0003_carga_etapas"
down_revision = "0002_ciudades_paradas"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    cities = sa.table(
        "ciudades", sa.column("id_ciudad", sa.Integer), sa.column("nombre", sa.String)
    )
    legacy = list(
        bind.execute(
            sa.text("SELECT id, trip_id, origin, destination, status FROM cargas")
        ).mappings()
    )
    prepared = []
    for row in legacy:
        origin = bind.scalar(sa.select(cities.c.id_ciudad).where(cities.c.nombre == row["origin"]))
        dest = bind.scalar(
            sa.select(cities.c.id_ciudad).where(cities.c.nombre == row["destination"])
        )
        if row["trip_id"] and (not origin or not dest):
            raise RuntimeError(
                "Una carga asignada necesita ciudades de origen/destino reconocibles antes de migrar"
            )
        prepared.append((row, origin, dest))
    for field in ("departamento", "provincia", "distrito"):
        op.add_column("ciudades", sa.Column(field, sa.String(100), nullable=True))
    with op.batch_alter_table("cargas") as batch:
        batch.add_column(sa.Column("origen_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("destino_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_cargas_origen_ciudad", "ciudades", ["origen_id"], ["id_ciudad"]
        )
        batch.create_foreign_key(
            "fk_cargas_destino_ciudad", "ciudades", ["destino_id"], ["id_ciudad"]
        )
        batch.create_index("ix_cargas_origen_id", ["origen_id"])
        batch.create_index("ix_cargas_destino_id", ["destino_id"])
    op.create_table(
        "detalle_carga_viajes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("id_carga", sa.String(36), sa.ForeignKey("cargas.id"), nullable=False),
        sa.Column("id_viaje", sa.String(36), sa.ForeignKey("viajes.id"), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("origen_id", sa.Integer(), sa.ForeignKey("ciudades.id_ciudad"), nullable=False),
        sa.Column("destino_id", sa.Integer(), sa.ForeignKey("ciudades.id_ciudad"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="pendiente"),
        sa.Column("salida_real", sa.DateTime(timezone=True), nullable=True),
        sa.Column("llegada_real", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.UniqueConstraint("id_carga", "orden", name="uq_carga_etapa_orden"),
        sa.UniqueConstraint("id_carga", "id_viaje", name="uq_carga_etapa_viaje"),
        sa.CheckConstraint(
            "estado IN ('pendiente', 'en_transito', 'completado', 'cancelado')",
            name="ck_etapa_estado",
        ),
        sa.CheckConstraint("orden > 0", name="ck_etapa_orden"),
        sa.CheckConstraint("origen_id <> destino_id", name="ck_etapa_extremos"),
    )
    op.create_index("ix_detalle_carga_viajes_id_carga", "detalle_carga_viajes", ["id_carga"])
    op.create_index("ix_detalle_carga_viajes_id_viaje", "detalle_carga_viajes", ["id_viaje"])
    table = sa.table(
        "detalle_carga_viajes",
        sa.column("id", sa.String),
        sa.column("id_carga", sa.String),
        sa.column("id_viaje", sa.String),
        sa.column("orden", sa.Integer),
        sa.column("origen_id", sa.Integer),
        sa.column("destino_id", sa.Integer),
        sa.column("estado", sa.String),
        sa.column("salida_real", sa.DateTime),
        sa.column("llegada_real", sa.DateTime),
        sa.column("data", sa.JSON),
    )
    for row, origin, dest in prepared:
        bind.execute(
            sa.text("UPDATE cargas SET origen_id=:o,destino_id=:d WHERE id=:id"),
            dict(o=origin, d=dest, id=row["id"]),
        )
        if row["trip_id"]:
            trip = (
                bind.execute(
                    sa.text(
                        "SELECT route_id,actual_start_at,actual_end_at FROM viajes WHERE id=:id"
                    ),
                    dict(id=row["trip_id"]),
                )
                .mappings()
                .one()
            )
            path = (
                list(
                    bind.scalars(
                        sa.text("SELECT origen_id FROM rutas WHERE id=:id"),
                        dict(id=trip["route_id"]),
                    )
                )
                + list(
                    bind.scalars(
                        sa.text("SELECT ciudad_id FROM paradas WHERE id_ruta=:id ORDER BY orden"),
                        dict(id=trip["route_id"]),
                    )
                )
                + list(
                    bind.scalars(
                        sa.text("SELECT destino_id FROM rutas WHERE id=:id"),
                        dict(id=trip["route_id"]),
                    )
                )
            )
            if origin not in path or dest not in path or path.index(origin) >= path.index(dest):
                raise RuntimeError(
                    "Una carga legacy no coincide con el recorrido; corregir antes de migrar"
                )
            state = {
                "entregada": "completado",
                "en_transito": "en_transito",
                "cancelada": "cancelado",
            }.get(row["status"], "pendiente")
            bind.execute(
                table.insert().values(
                    id=str(uuid4()),
                    id_carga=row["id"],
                    id_viaje=row["trip_id"],
                    orden=1,
                    origen_id=origin,
                    destino_id=dest,
                    estado=state,
                    salida_real=trip["actual_start_at"],
                    llegada_real=trip["actual_end_at"],
                    data={"migrada": True},
                )
            )


def downgrade():
    bind = op.get_bind()
    if bind.scalar(
        sa.text(
            "SELECT COUNT(*) FROM (SELECT id_carga FROM detalle_carga_viajes GROUP BY id_carga HAVING COUNT(*)>1) x"
        )
    ):
        raise RuntimeError(
            "No se puede volver al modelo de un viaje mientras existan cargas con varias etapas"
        )
    op.drop_table("detalle_carga_viajes")
    with op.batch_alter_table("cargas") as batch:
        batch.drop_index("ix_cargas_origen_id")
        batch.drop_index("ix_cargas_destino_id")
        batch.drop_constraint("fk_cargas_origen_ciudad", type_="foreignkey")
        batch.drop_constraint("fk_cargas_destino_ciudad", type_="foreignkey")
        batch.drop_column("origen_id")
        batch.drop_column("destino_id")
    for field in ("departamento", "provincia", "distrito"):
        op.drop_column("ciudades", field)
