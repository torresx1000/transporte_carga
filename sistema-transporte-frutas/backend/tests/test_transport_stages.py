import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.core.database import Base, get_db
from app.core.permissions import get_current_user
from app.models.entities import Client, Driver, Vehicle, Load, User
from app.models.rutas.rutas import City
from app.api.v1.endpoints.cargas import cargas as endpoints


class TransportStagesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(self.engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([City(nombre=name) for name in ["Ica", "Pisco", "Cañete", "Lima"]])
        self.db.add_all(
            [
                Client(id="c", name="Cliente", status="activo", data={}),
                Vehicle(id="v", plate="ABC-123", capacity_kg=1000, status="disponible", data={}),
                Driver(id="d", name="Conductor", status="disponible", data={}),
            ]
        )
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: User(
            id="a", email="a@test.test", role="admin", active=True, data={}
        )
        self.client = TestClient(app)
        self.tmp = tempfile.TemporaryDirectory()
        self.old_storage = endpoints.STORAGE
        endpoints.STORAGE = Path(self.tmp.name)
        r = self.client.post(
            "/api/v1/rutas",
            json=dict(
                codigo="R-001",
                nombre="Ica - Lima",
                origen_id=1,
                destino_id=4,
                distancia_km="300",
                duracion_minutos=300,
                paradas=[dict(ciudad_id=2, orden=1), dict(ciudad_id=3, orden=2)],
            ),
        )
        self.assertEqual(r.status_code, 201, r.text)
        self.route = r.json()["id"]

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        endpoints.STORAGE = self.old_storage
        self.tmp.cleanup()

    def load(self, origin=1, dest=4, weight=600):
        r = self.client.post(
            "/api/v1/cargas",
            json=dict(
                cliente_id="c",
                producto="Palta",
                cantidad=30,
                unidad="jaba",
                peso_neto_total_kg=str(weight),
                procedencia="Recojo",
                destino="Entrega",
                origen_id=origin,
                destino_id=dest,
                contacto="Ana",
                origen_distrito="Ica",
                temperatura="8",
                jabas_despachadas=31,
            ),
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def trip(self, day=1, loads=None):
        r = self.client.post(
            "/api/v1/viajes",
            json=dict(
                vehiculo_id="v",
                conductor_id="d",
                ruta_id=self.route,
                fecha_salida_programada=f"2026-11-{day:02}T08:00:00Z",
                fecha_entrega_estimada=f"2026-11-{day:02}T14:00:00Z",
                cargas_ids=loads or [],
            ),
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["id"]

    def plan(self, id, legs):
        return self.client.put(
            f"/api/v1/cargas/{id}/etapas",
            json={"etapas": [dict(viaje_id=t, origen_id=o, destino_id=d) for t, o, d in legs]},
        )

    def test_three_transfers_single_load_and_progress(self):
        load = self.load()
        trips = [self.trip(i) for i in (1, 2, 3)]
        r = self.plan(load, [(trips[0], 1, 2), (trips[1], 2, 3), (trips[2], 3, 4)])
        self.assertEqual(r.status_code, 200, r.text)
        for index, trip in enumerate(trips):
            r = self.client.post(f"/api/v1/viajes/{trip}/estado", json={"estado": "en_curso"})
            self.assertEqual(r.status_code, 200, r.text)
            stage = self.client.get(f"/api/v1/cargas/{load}/etapas").json()[index]
            if stage["estado"] == "pendiente":
                r = self.client.post(
                    f"/api/v1/cargas/{load}/etapas/{stage['id']}/estado",
                    json={"estado": "en_transito"},
                )
                self.assertEqual(r.status_code, 200, r.text)
            r = self.client.post(
                f"/api/v1/cargas/{load}/etapas/{stage['id']}/estado", json={"estado": "completado"}
            )
            self.assertEqual(r.status_code, 200, r.text)
            state = self.client.get(f"/api/v1/cargas/{load}").json()["estado"]
            self.assertEqual(state, "entregada" if index == 2 else "asignada")
            r = self.client.post(f"/api/v1/viajes/{trip}/estado", json={"estado": "entregado"})
            self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(self.db.scalars(select(Load)).all()), 1)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="u", email="u@test.test", role="cliente", active=True, data={"client_id": "c"}
        )
        r = self.client.get("/api/v1/portal/viajes")
        self.assertEqual(len(r.json()), 3)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="u2", email="u2@test.test", role="cliente", active=True, data={"client_id": "other"}
        )
        self.assertEqual(self.client.get("/api/v1/portal/viajes").json(), [])

    def test_continuity_direction_order_and_temporal_validation(self):
        load = self.load()
        a, b = self.trip(1), self.trip(2)
        for legs in [
            [(a, 1, 2), (b, 3, 4)],
            [(a, 2, 1)],
            [(b, 1, 2), (a, 2, 4)],
            [(a, 1, 2), (a, 2, 4)],
            [(a, 1, 4), (b, 4, 3)],
        ]:
            r = self.plan(load, legs)
            self.assertEqual(r.status_code, 422, r.text)
        self.assertEqual(self.client.get(f"/api/v1/cargas/{load}/etapas").json(), [])
        self.assertEqual(self.plan(load, [(a, 1, 2), (b, 2, 4)]).status_code, 200)
        r = self.client.post(f"/api/v1/viajes/{b}/estado", json={"estado": "en_curso"})
        # Pickup at an intermediate stop cannot progress before previous completion.
        self.assertEqual(r.status_code, 200, r.text)
        stage = self.client.get(f"/api/v1/cargas/{load}/etapas").json()[1]
        r = self.client.post(
            f"/api/v1/cargas/{load}/etapas/{stage['id']}/estado", json={"estado": "en_transito"}
        )
        self.assertEqual(r.status_code, 409, r.text)

    def test_capacity_is_per_segment_and_overload_is_atomic(self):
        a = self.load(1, 2)
        b = self.load(2, 4)
        c = self.load(1, 4)
        trip = self.trip()
        self.assertEqual(self.plan(a, [(trip, 1, 2)]).status_code, 200)
        r = self.plan(b, [(trip, 2, 4)])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(
            float(self.client.get(f"/api/v1/viajes/{trip}").json()["peso_total_kg"]), 600
        )
        r = self.plan(c, [(trip, 1, 4)])
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.client.get(f"/api/v1/cargas/{c}/etapas").json(), [])
        r = self.client.patch(f"/api/v1/cargas/{a}", json={"peso_neto_total_kg": "1100"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(
            float(self.client.get(f"/api/v1/cargas/{a}").json()["peso_neto_total_kg"]), 600
        )

    def test_pending_create_assignment_cancel_and_metadata(self):
        load = self.load()
        record = self.client.get(f"/api/v1/cargas/{load}").json()
        self.assertEqual(record["estado"], "pendiente")
        self.assertEqual(record["contacto"], "Ana")
        self.assertEqual(record["jabas_despachadas"], 31)
        r = self.client.patch(f"/api/v1/cargas/{load}", json={"origen_direccion": "Mercado"})
        self.assertEqual(r.status_code, 200, r.text)
        trip = self.trip(loads=[load])
        self.assertEqual(len(self.client.get(f"/api/v1/viajes/{trip}").json()["etapas"]), 1)
        r = self.client.post(f"/api/v1/viajes/{trip}/estado", json={"estado": "cancelado"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get(f"/api/v1/cargas/{load}").json()["estado"], "pendiente")

    def test_append_after_transfer_and_freeze_history(self):
        load = self.load()
        a = self.trip(1)
        b = self.trip(2)
        self.assertEqual(self.plan(load, [(a, 1, 2)]).status_code, 200)
        self.assertEqual(
            self.client.post(f"/api/v1/viajes/{a}/estado", json={"estado": "en_curso"}).status_code,
            200,
        )
        stage = self.client.get(f"/api/v1/cargas/{load}/etapas").json()[0]
        self.assertEqual(
            self.client.post(
                f"/api/v1/cargas/{load}/etapas/{stage['id']}/estado", json={"estado": "completado"}
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get(f"/api/v1/cargas/{load}").json()["estado"], "pendiente")
        r = self.plan(load, [(a, 1, 2), (b, 2, 4)])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()[0]["id"], stage["id"])
        self.assertEqual(self.plan(load, [(b, 1, 4)]).status_code, 409)
        r = self.client.patch(f"/api/v1/rutas/{self.route}", json={"paradas": []})
        self.assertEqual(r.status_code, 409, r.text)
        r = self.client.patch(f"/api/v1/rutas/{self.route}", json={"nombre": "Ruta costera"})
        self.assertEqual(r.status_code, 200, r.text)

    def test_trip_update_preserves_stage_schedule(self):
        load = self.load()
        a, b = self.trip(1), self.trip(2)
        self.assertEqual(self.plan(load, [(a, 1, 2), (b, 2, 4)]).status_code, 200)
        r = self.client.patch(
            f"/api/v1/viajes/{a}", json={"fecha_entrega_estimada": "2026-11-03T14:00:00Z"}
        )
        self.assertEqual(r.status_code, 409, r.text)
        self.assertTrue(
            self.client.get(f"/api/v1/viajes/{a}")
            .json()["fecha_entrega_estimada"]
            .startswith("2026-11-01")
        )

    def test_load_errors_identify_the_field(self):
        load = self.load()
        for patch, field in [
            ({"destino_id": 1}, "destino_id"),
            ({"origen_id": 999}, "origen_id"),
            ({"cliente_id": "unknown"}, "cliente_id"),
            ({"peso_bruto_total_kg": "1"}, "peso_bruto_total_kg"),
            ({"fecha_recojo": "2026-11-02", "fecha_entrega": "2026-11-01"}, "fecha_entrega"),
        ]:
            response = self.client.patch(f"/api/v1/cargas/{load}", json=patch)
            self.assertIn(response.status_code, [409, 422], response.text)
            self.assertEqual(response.json()["details"]["field"], field)

    def test_files_persist_download_and_access_control(self):
        load = self.load()
        r = self.client.post(
            f"/api/v1/cargas/{load}/documentos",
            files={"archivo": ("guia.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        self.assertEqual(r.status_code, 201, r.text)
        id = r.json()["id"]
        url = f"/api/v1/cargas/{load}/documentos/{id}/archivo"
        self.assertEqual(self.client.get(url).content, b"%PDF-1.4 test")
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())), 1)
        r = self.client.post(
            f"/api/v1/cargas/{load}/documentos", files={"archivo": ("bad.exe", b"binary")}
        )
        self.assertEqual(r.status_code, 422)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="u", email="u@test.test", role="cliente", active=True, data={"client_id": "other"}
        )
        self.assertEqual(self.client.get(url).status_code, 404)
        app.dependency_overrides[get_current_user] = lambda: User(
            id="u", email="u@test.test", role="cliente", active=True, data={"client_id": "c"}
        )
        self.assertEqual(self.client.get(url).status_code, 200)


if __name__ == "__main__":
    unittest.main()
