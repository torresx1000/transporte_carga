import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.permissions import get_current_user
from app.main import app
from app.models.entities import User


class VehicleTrailerApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: User(
            id="admin-test", email="admin@test.test", role="admin", active=True, data={}
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def vehicle_payload(self, **changes):
        return {
            "codigo_flota": "V-88",
            "placa": "ABC-123",
            "tipo": "Camión",
            "capacidad_kg": 12000,
            "tiene_remolque": True,
            "placa_remolque": "xyz-987",
            **changes,
        }

    def test_create_vehicle_with_trailer_saves_normalized_plate(self):
        response = self.client.post("/api/v1/vehiculos", json=self.vehicle_payload())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertTrue(response.json()["tiene_remolque"])
        self.assertEqual(response.json()["placa_remolque"], "XYZ-987")

    def test_create_vehicle_without_trailer_omits_plate(self):
        response = self.client.post(
            "/api/v1/vehiculos", json=self.vehicle_payload(tiene_remolque=False)
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertFalse(response.json()["tiene_remolque"])
        self.assertIsNone(response.json()["placa_remolque"])

    def test_trailer_requires_plate(self):
        payload = self.vehicle_payload(placa_remolque=None)
        response = self.client.post("/api/v1/vehiculos", json=payload)
        self.assertEqual(response.status_code, 422, response.text)

    def test_disabling_trailer_clears_persisted_plate(self):
        created = self.client.post("/api/v1/vehiculos", json=self.vehicle_payload())
        self.assertEqual(created.status_code, 201, created.text)
        vehicle_id = created.json()["id"]
        response = self.client.patch(
            f"/api/v1/vehiculos/{vehicle_id}", json={"tiene_remolque": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["tiene_remolque"])
        self.assertIsNone(response.json()["placa_remolque"])
