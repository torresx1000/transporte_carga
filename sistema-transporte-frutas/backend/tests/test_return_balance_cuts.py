import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.permissions import get_current_user
from app.main import app
from app.models.entities import Client, Load, ReturnRecord, User
from app.models.enums import LoadStatus, Priority
from app.models.rutas.rutas import City


class ReturnBalanceCutTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all(
            [
                Client(id="client-1", name="Cliente Uno", status="activo", data={}),
                City(id_ciudad=1, nombre="Ica"),
                City(id_ciudad=2, nombre="Lima"),
                Load(
                    id="old-load",
                    code="CAR-OLD",
                    client_id="client-1",
                    status=LoadStatus.PENDING,
                    priority=Priority.NORMAL,
                    jabas_dispatched=12,
                    product="Palta",
                    quantity=12,
                    unit="jaba",
                    origin="Ica",
                    destination="Lima",
                    data={},
                ),
                ReturnRecord(
                    id="old-return",
                    client_id="client-1",
                    load_id="old-load",
                    returned_total=5,
                    data={},
                ),
            ]
        )
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: User(
            id="admin-1", email="admin@test.test", role="admin", active=True, data={}
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_cut_archives_previous_totals_and_counts_only_new_activity(self):
        before = self.client.get("/api/v1/retornos/saldos-por-cliente")
        self.assertEqual(before.status_code, 200, before.text)
        self.assertEqual(before.json()[0]["total_despachadas"], 12)
        self.assertEqual(before.json()[0]["total_retornadas"], 5)

        cut_response = self.client.post(
            "/api/v1/retornos/clientes/client-1/reiniciar-saldo"
        )
        self.assertEqual(cut_response.status_code, 201, cut_response.text)
        cut = cut_response.json()
        self.assertEqual(cut["total_despachadas"], 12)
        self.assertEqual(cut["total_retornadas"], 5)
        self.assertEqual(cut["numero_corte"], 1)

        after_cut = self.client.get("/api/v1/retornos/saldos-por-cliente")
        self.assertEqual(after_cut.status_code, 200, after_cut.text)
        self.assertEqual(after_cut.json()[0]["total_despachadas"], 0)
        self.assertEqual(after_cut.json()[0]["total_retornadas"], 0)
        self.assertEqual(after_cut.json()[0]["periodo_id"], cut["id"])

        new_load = self.client.post(
            "/api/v1/cargas",
            json={
                "cliente_id": "client-1",
                "producto": "Palta",
                "cantidad": 8,
                "unidad": "jaba",
                "procedencia": "Ica",
                "destino": "Lima",
                "origen_id": 1,
                "destino_id": 2,
                "jabas_despachadas": 8,
            },
        )
        self.assertEqual(new_load.status_code, 201, new_load.text)
        self.assertEqual(new_load.json()["periodo_retorno_id"], cut["id"])

        old_load_return = self.client.post(
            "/api/v1/retornos",
            json={"data": {"cliente_id": "client-1", "carga_id": "old-load", "sueltas": 2}},
        )
        self.assertEqual(old_load_return.status_code, 422, old_load_return.text)

        new_return = self.client.post(
            "/api/v1/retornos",
            json={
                "data": {
                    "cliente_id": "client-1",
                    "carga_id": new_load.json()["id"],
                    "paquetes_3": 2,
                }
            },
        )
        self.assertEqual(new_return.status_code, 201, new_return.text)

        current = self.client.get("/api/v1/retornos/saldos-por-cliente")
        self.assertEqual(current.status_code, 200, current.text)
        self.assertEqual(current.json()[0]["total_despachadas"], 8)
        self.assertEqual(current.json()[0]["total_retornadas"], 6)

        archived = self.client.get("/api/v1/retornos/historial-cortes")
        self.assertEqual(archived.status_code, 200, archived.text)
        self.assertEqual(archived.json()[0]["id"], cut["id"])
        self.assertEqual(archived.json()[0]["usuario_email"], "admin@test.test")

    def test_only_admin_can_reset_a_client_balance(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id="operator-1", email="operator@test.test", role="operador", active=True, data={}
        )
        response = self.client.post(
            "/api/v1/retornos/clientes/client-1/reiniciar-saldo"
        )
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
