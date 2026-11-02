"""Normalize route cities and intermediate stops without replacing route IDs."""

import json
from alembic import op
import sqlalchemy as sa

revision = "0002_ciudades_paradas"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    routes = list(
        bind.execute(sa.text("SELECT id, origin, destination, data FROM rutas")).mappings()
    )
    prepared = []
    for route in routes:
        data = route["data"] or {}
        if isinstance(data, str):
            data = json.loads(data)
        stops = data.get("paradas", []) or []
        if not isinstance(stops, list) or any(not isinstance(p, str) for p in stops):
            raise RuntimeError("Formato legacy de paradas no reconocido; revisar antes de migrar")
        names = [route["origin"], route["destination"], *stops]
        if any(not isinstance(n, str) or not n.strip() or len(n.strip()) > 100 for n in names):
            raise RuntimeError("Revisa ciudades vacías o mayores de 100 caracteres antes de migrar")
        prepared.append((route["id"], [n.strip() for n in names]))
    op.create_table(
        "ciudades",
        sa.Column("id_ciudad", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.UniqueConstraint("nombre"),
    )
    op.add_column("rutas", sa.Column("origen_id", sa.Integer(), nullable=True))
    op.add_column("rutas", sa.Column("destino_id", sa.Integer(), nullable=True))
    op.create_table(
        "paradas",
        sa.Column("id_parada", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id_ruta", sa.String(36), sa.ForeignKey("rutas.id"), nullable=False),
        sa.Column("ciudad_id", sa.Integer(), sa.ForeignKey("ciudades.id_ciudad"), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("tiempo_espera", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("id_ruta", "orden", name="uq_paradas_ruta_orden"),
        sa.CheckConstraint("orden > 0", name="ck_paradas_orden"),
        sa.CheckConstraint("tiempo_espera >= 0", name="ck_paradas_espera"),
    )
    cities = sa.table(
        "ciudades", sa.column("id_ciudad", sa.Integer), sa.column("nombre", sa.String)
    )
    stops_table = sa.table(
        "paradas",
        sa.column("id_ruta", sa.String),
        sa.column("ciudad_id", sa.Integer),
        sa.column("orden", sa.Integer),
        sa.column("tiempo_espera", sa.Integer),
    )

    def city_id(name):
        # Use database collation for matching, including MySQL accent/case rules.
        found = bind.scalar(sa.select(cities.c.id_ciudad).where(cities.c.nombre == name))
        if found is None:
            bind.execute(cities.insert().values(nombre=name))
            found = bind.scalar(sa.select(cities.c.id_ciudad).where(cities.c.nombre == name))
        return found

    for route_id, names in prepared:
        ids = [city_id(name) for name in names]
        bind.execute(
            sa.text("UPDATE rutas SET origen_id=:o, destino_id=:d WHERE id=:id"),
            dict(o=ids[0], d=ids[1], id=route_id),
        )
        # Endpoints stay in rutas; preserve original JSON for compatibility/rollback.
        intermediate = [i for i in ids[2:] if i not in ids[:2]]
        for order, ident in enumerate(intermediate, 1):
            bind.execute(
                stops_table.insert().values(
                    id_ruta=route_id, ciudad_id=ident, orden=order, tiempo_espera=0
                )
            )
    with op.batch_alter_table("rutas") as batch:
        batch.alter_column("origen_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("destino_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_rutas_origen_ciudad", "ciudades", ["origen_id"], ["id_ciudad"])
        batch.create_foreign_key(
            "fk_rutas_destino_ciudad", "ciudades", ["destino_id"], ["id_ciudad"]
        )
        batch.create_index("ix_rutas_origen_id", ["origen_id"])
        batch.create_index("ix_rutas_destino_id", ["destino_id"])
    op.create_index("ix_paradas_id_ruta", "paradas", ["id_ruta"])
    op.create_index("ix_paradas_ciudad_id", "paradas", ["ciudad_id"])


def downgrade():
    # Keep current normalized stops readable by the previous application.
    bind = op.get_bind()
    for route in bind.execute(sa.text("SELECT id, data FROM rutas")).mappings():
        data = route["data"] or {}
        if isinstance(data, str):
            data = json.loads(data)
        data["paradas"] = list(
            bind.scalars(
                sa.text(
                    "SELECT c.nombre FROM paradas p JOIN ciudades c ON c.id_ciudad=p.ciudad_id WHERE p.id_ruta=:id ORDER BY p.orden"
                ),
                {"id": route["id"]},
            )
        )
        bind.execute(
            sa.text("UPDATE rutas SET data=:data WHERE id=:id"),
            {"data": json.dumps(data), "id": route["id"]},
        )
    op.drop_table("paradas")
    with op.batch_alter_table("rutas") as batch:
        batch.drop_index("ix_rutas_origen_id")
        batch.drop_index("ix_rutas_destino_id")
        batch.drop_constraint("fk_rutas_origen_ciudad", type_="foreignkey")
        batch.drop_constraint("fk_rutas_destino_ciudad", type_="foreignkey")
        batch.drop_column("origen_id")
        batch.drop_column("destino_id")
    op.drop_table("ciudades")
