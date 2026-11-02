"""Create development-only sample accounts for each application role."""

import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import Client, User

ALLOWED_ENVIRONMENTS = {"development", "dev", "local", "test"}


def require_development_environment(environment: str) -> None:
    if environment.strip().lower() not in ALLOWED_ENVIRONMENTS:
        sys.exit("Seed de demostración bloqueado: define APP_ENV=development, dev, local o test.")

CLIENT_DOCUMENT = "20123456789"
DEFAULT_ADMIN = ("admin.demo@transfrutas.local", "DemoAdmin2026!")
SAMPLE_ACCOUNTS = (
    ("operador.demo@transfrutas.local", "DemoOperador2026!", "operador", "Operador demo"),
    ("chofer.demo@transfrutas.local", "DemoChofer2026!", "chofer", "Chofer demo"),
    ("cliente.demo@transfrutas.local", "DemoCliente2026!", "cliente", "Cliente demo"),
)


def main() -> None:
    require_development_environment(settings.APP_ENV)
    file_values = dotenv_values(Path(__file__).with_name(".env"))
    admin_email = os.getenv("ADMIN_EMAIL") or file_values.get("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD") or file_values.get("ADMIN_PASSWORD")
    if bool(admin_email) != bool(admin_password):
        sys.exit("Configura ADMIN_EMAIL y ADMIN_PASSWORD juntos, o deja ambos sin definir para usar las credenciales documentadas.")
    admin = (str(admin_email).strip().lower(), str(admin_password)) if admin_email and admin_password else DEFAULT_ADMIN
    accounts = ((admin[0], admin[1], "admin", "Administrador demo"), *SAMPLE_ACCOUNTS)
    with SessionLocal() as db:
        client = db.scalar(select(Client).where(Client.document == CLIENT_DOCUMENT))
        if client is None:
            client = Client(
                name="Cliente de demostración",
                document=CLIENT_DOCUMENT,
                status="activo",
                data={
                    "nombre": "Cliente de demostración",
                    "documento": CLIENT_DOCUMENT,
                    "tipo_documento": "RUC",
                    "tipo": "Empresa",
                    "estado": "activo",
                    "telefono": "+51 900 000 001",
                    "correo": "cliente.demo@transfrutas.local",
                    "departamento": "Lima",
                    "ubicacion": "Lima",
                },
            )
            db.add(client)
            db.flush()

        for email, password, role, name in accounts:
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                if existing.role != role:
                    db.rollback()
                    sys.exit(f"La cuenta {email} ya existe con un rol distinto; no se modificó.")
                if role == "cliente" and existing.data.get("client_id") != client.id:
                    existing.data = {**existing.data, "client_id": client.id}
                print(f"Ya existe: {email} ({role}).")
                continue
            db.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    active=True,
                    data={"name": name, "client_id": client.id if role == "cliente" else None},
                )
            )
            print(f"Creado: {email} ({role}).")
        db.commit()


if __name__ == "__main__":
    main()
