from pathlib import Path
from uuid import uuid4
import os

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.records import build_resource_router
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.entities import Document, Expense, Trip, User

router = build_resource_router("gastos")
STORAGE = Path(
    os.environ.get("GASTOS_STORAGE_DIR", str(Path(__file__).resolve().parents[5] / "storage" / "gastos"))
)
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".xlsx"}
access = require_roles("admin", "operador")


@router.get("/viaje/{trip_id}")
def trip_expenses(trip_id: str, db: Session = Depends(get_db), user: User = Depends(access)):
    trip = db.get(Trip, trip_id)
    if not trip or trip.deleted_at:
        raise HTTPException(404, "Viaje no encontrado")
    expenses = db.scalars(
        select(Expense)
        .where(Expense.trip_id == trip_id, Expense.deleted_at.is_(None))
        .order_by(Expense.created_at.desc())
    ).all()
    return [
        {
            "id": expense.id,
            "viaje_id": expense.trip_id,
            "monto_centimos": expense.amount,
            "motivo": expense.category,
            "detalle": expense.data.get("detalle", ""),
            "created_at": expense.created_at,
            "created_by": expense.created_by,
        }
        for expense in expenses
    ]


@router.get("/{expense_id}/documentos")
def expense_documents(expense_id: str, db: Session = Depends(get_db), user: User = Depends(access)):
    expense = db.get(Expense, expense_id)
    if not expense or expense.deleted_at:
        raise HTTPException(404, "Gasto no encontrado")
    docs = db.scalars(
        select(Document).where(
            Document.owner_type == "gasto",
            Document.owner_id == expense_id,
            Document.deleted_at.is_(None),
        )
    ).all()
    return [{"id": doc.id, "nombre": doc.data.get("nombre"), "tamano": doc.data.get("tamano")} for doc in docs]


@router.post("/{expense_id}/documentos", status_code=201)
async def upload_expense_document(
    expense_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(access),
):
    expense = db.get(Expense, expense_id)
    if not expense or expense.deleted_at:
        raise HTTPException(404, "Gasto no encontrado")
    name = Path((archivo.filename or "archivo").replace(chr(92), "/")).name
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, "Formato no permitido")
    STORAGE.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex
    path = STORAGE / key
    size = 0
    try:
        with path.open("xb") as stream:
            while chunk := await archivo.read(1024 * 1024):
                size += len(chunk)
                if size > 10 * 1024 * 1024:
                    raise HTTPException(413, "El archivo supera 10 MB")
                stream.write(chunk)
        if size == 0:
            raise HTTPException(422, "El archivo está vacío")
        doc = Document(
            owner_type="gasto",
            owner_id=expense_id,
            document_type="comprobante_gasto",
            created_by=user.id,
            data={"nombre": name, "storage_key": key, "tamano": size},
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return {"id": doc.id, "nombre": name, "tamano": size}
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    finally:
        await archivo.close()


@router.get("/{expense_id}/documentos/{document_id}/archivo")
def download_expense_document(
    expense_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(access),
):
    expense = db.get(Expense, expense_id)
    doc = db.get(Document, document_id)
    if (
        not expense
        or expense.deleted_at
        or not doc
        or doc.deleted_at
        or doc.owner_type != "gasto"
        or doc.owner_id != expense_id
    ):
        raise HTTPException(404, "Documento no encontrado")
    key = doc.data.get("storage_key", "")
    if len(key) != 32 or any(char not in "0123456789abcdef" for char in key):
        raise HTTPException(404, "Archivo no disponible")
    path = STORAGE / key
    if not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, filename=doc.data.get("nombre", "archivo"), media_type="application/octet-stream")
