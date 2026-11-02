"""Create the first administrator from ADMIN_EMAIL and ADMIN_PASSWORD env vars."""
import os
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User

email = os.getenv("ADMIN_EMAIL", "").strip().lower()
password = os.getenv("ADMIN_PASSWORD", "")
if not email or len(password) < 8:
    sys.exit("Define ADMIN_EMAIL y ADMIN_PASSWORD (mínimo 8 caracteres).")

with SessionLocal() as db:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        print("El usuario administrador ya existe.")
    else:
        db.add(User(email=email, password_hash=hash_password(password), role="admin", active=True, data={}))
        db.commit()
        print("Usuario administrador creado.")
