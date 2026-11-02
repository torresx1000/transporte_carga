import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.documentos import documentos as endpoints
from app.core.database import Base, get_db
from app.core.permissions import get_current_user
from app.main import app
from app.models.entities import Document, Expense, User, Vehicle
from app.models.viajes.viajes import Trip


class DocumentLibraryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add(
            Vehicle(
                id="vehicle-1",
                plate="ABC-123",
                fleet_code="F-01",
                status="disponible",
                data={},
            )
        )
        self.db.add(
            Trip(
                id="trip-1",
                code="VJ-001",
                vehicle_id="vehicle-1",
                driver_id="driver-1",
                route_id="route-1",
                status="programado",
                scheduled_start_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                scheduled_end_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
                data={},
            )
        )
        self.db.add(
            Expense(
                id="expense-1",
                trip_id="trip-1",
                vehicle_id="vehicle-1",
                amount=1000,
                category="Peaje",
                data={},
            )
        )
        self.db.add_all(
            [
                Document(
                    id="trip-file",
                    owner_type="viaje",
                    owner_id="trip-1",
                    document_type="archivo_viaje",
                    data={"nombre": "guia.pdf", "storage_key": "a" * 32, "tamano": 1024},
                ),
                Document(
                    id="expense-file",
                    owner_type="gasto",
                    owner_id="expense-1",
                    document_type="comprobante_gasto",
                    data={"nombre": "peaje.pdf", "storage_key": "b" * 32, "tamano": 2048},
                ),
            ]
        )
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: User(
            id="admin-1", email="admin@example.test", role="admin", active=True, data={}
        )
        self.client = TestClient(app)
        self.temp_storage = tempfile.TemporaryDirectory()
        self.previous_storage = endpoints.STORAGE
        endpoints.STORAGE = Path(self.temp_storage.name)

    def tearDown(self):
        app.dependency_overrides.clear()
        endpoints.STORAGE = self.previous_storage
        self.temp_storage.cleanup()
        self.db.close()
        self.engine.dispose()

    def test_vehicle_and_trip_folders_include_related_files(self):
        vehicle_files = self.client.get(
            "/api/v1/documentos/biblioteca",
            params={"carpeta": "vehiculo", "propietario_id": "vehicle-1"},
        )
        self.assertEqual(vehicle_files.status_code, 200, vehicle_files.text)
        self.assertEqual({item["id"] for item in vehicle_files.json()}, {"trip-file", "expense-file"})

        trip_files = self.client.get(
            "/api/v1/documentos/biblioteca",
            params={"carpeta": "viaje", "propietario_id": "trip-1"},
        )
        self.assertEqual(trip_files.status_code, 200, trip_files.text)
        self.assertEqual({item["id"] for item in trip_files.json()}, {"trip-file", "expense-file"})

    def test_upload_to_trip_folder_is_listed_and_downloadable(self):
        response = self.client.post(
            "/api/v1/documentos/biblioteca",
            params={"propietario_tipo": "viaje", "propietario_id": "trip-1"},
            files={"archivo": ("acta.txt", b"contenido de prueba", "text/plain")},
        )
        self.assertEqual(response.status_code, 201, response.text)
        document_id = response.json()["id"]

        listing = self.client.get(
            "/api/v1/documentos/biblioteca",
            params={"carpeta": "viaje", "propietario_id": "trip-1"},
        )
        self.assertIn(document_id, {item["id"] for item in listing.json()})

        download = self.client.get(
            f"/api/v1/documentos/biblioteca/{document_id}/archivo"
        )
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, b"contenido de prueba")


if __name__ == "__main__":
    unittest.main()
