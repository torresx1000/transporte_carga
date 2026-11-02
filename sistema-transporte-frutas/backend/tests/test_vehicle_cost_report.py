from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.permissions import get_current_user
from app.main import app
from app.models.entities import Trip, User, Vehicle
from app.models.enums import TripStatus


class VehicleCostReportTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add(
            Vehicle(id="truck-1", plate="ABC-123", status="disponible", data={})
        )
        self.db.add(
            Trip(
                id="trip-1",
                code="VJ-TEST-1",
                vehicle_id="truck-1",
                status=TripStatus.SCHEDULED,
                scheduled_start_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                scheduled_end_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
                data={},
            )
        )
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: User(
            id="admin-test", email="admin@test.test", role="admin", active=True, data={}
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_vehicle_report_includes_fuel_and_trip_expenses(self):
        fuel = self.client.post(
            "/api/v1/combustible",
            json={
                "data": {
                    "viaje_id": "trip-1",
                    "vehiculo_id": "truck-other",
                    "litros_milesimas": 25000,
                    "precio_centimos": 18500,
                    "odometro": 1200,
                    "fecha_consumo": "2026-11-01",
                }
            },
        )
        self.assertEqual(fuel.status_code, 201, fuel.text)
        self.assertEqual(fuel.json()["vehiculo_id"], "truck-1")

        expense = self.client.post(
            "/api/v1/gastos",
            json={
                "data": {
                    "viaje_id": "trip-1",
                    "monto_centimos": 4500,
                    "categoria": "Peaje",
                    "detalle": "Peaje de carretera",
                }
            },
        )
        self.assertEqual(expense.status_code, 201, expense.text)
        self.assertEqual(expense.json()["vehiculo_id"], "truck-1")

        report = self.client.get("/api/v1/reportes/costos-vehiculo/truck-1")
        self.assertEqual(report.status_code, 200, report.text)
        body = report.json()
        self.assertEqual(body["placa"], "ABC-123")
        self.assertEqual(body["total_centimos"], 23000)
        self.assertEqual({item["tipo"] for item in body["items"]}, {"combustible", "gasto"})
        self.assertTrue(all(item["viaje_codigo"] == "VJ-TEST-1" for item in body["items"]))

    def test_cost_records_require_a_trip_with_vehicle(self):
        response = self.client.post(
            "/api/v1/combustible",
            json={"data": {"vehiculo_id": "truck-1", "litros_milesimas": 1000}},
        )
        self.assertEqual(response.status_code, 422, response.text)

    def test_partial_payment_can_be_edited_without_changing_its_paid_balance(self):
        created = self.client.post(
            "/api/v1/pagos",
            json={
                "data": {
                    "viaje_id": "trip-1",
                    "sentido": "pago_transportista",
                    "monto_centimos": 10000,
                    "monto_acordado_centimos": 10000,
                    "monto_pagado_centimos": 4000,
                    "saldo_centimos": 6000,
                    "estado": "parcial",
                }
            },
        )
        self.assertEqual(created.status_code, 201, created.text)

        updated = self.client.patch(
            f"/api/v1/pagos/{created.json()['id']}",
            json={
                "data": {
                    "concepto": "Flete tercero",
                    "monto_centimos": 12000,
                    "monto_acordado_centimos": 12000,
                    "monto_pagado_centimos": 4000,
                    "saldo_centimos": 8000,
                    "estado": "parcial",
                }
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["concepto"], "Flete tercero")
        self.assertEqual(updated.json()["monto_pagado_centimos"], 4000)
        self.assertEqual(updated.json()["saldo_centimos"], 8000)
        self.assertEqual(updated.json()["estado"], "parcial")


if __name__ == "__main__":
    unittest.main()
