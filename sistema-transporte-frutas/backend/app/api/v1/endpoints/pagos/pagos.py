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
from app.models.entities import Document, Payment, User

router = build_resource_router("pagos")

STORAGE = Path(
    os.environ.get(
        "PAGOS_STORAGE_DIR", str(Path(__file__).resolve().parents[5] / "storage" / "pagos")
    )
)
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".xlsx"}
admin_or_operator = require_roles("admin", "operador")


@router.get("/{payment_id}/documentos")
def payment_documents(
    payment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    payment = db.get(Payment, payment_id)
    if not payment or payment.deleted_at:
        raise HTTPException(404, "Pago no encontrado")
    return [
        {"id": doc.id, "nombre": doc.data.get("nombre"), "tamano": doc.data.get("tamano")}
        for doc in db.scalars(
            select(Document).where(
                Document.owner_type == "pago",
                Document.owner_id == payment_id,
                Document.deleted_at.is_(None),
            )
        ).all()
    ]


@router.post("/{payment_id}/documentos", status_code=201)
async def upload_payment_document(
    payment_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    payment = db.get(Payment, payment_id)
    if not payment or payment.deleted_at:
        raise HTTPException(404, "Pago no encontrado")
    name = Path((archivo.filename or "archivo").replace(chr(92), "/")).name
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, "Formato permitido: PDF, imágenes JPG/PNG/WEBP, DOCX o XLSX")
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
            owner_type="pago",
            owner_id=payment_id,
            document_type="comprobante_pago",
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


@router.get("/{payment_id}/documentos/{document_id}/archivo")
def download_payment_document(
    payment_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    payment = db.get(Payment, payment_id)
    doc = db.get(Document, document_id)
    if (
        not payment
        or payment.deleted_at
        or not doc
        or doc.deleted_at
        or doc.owner_type != "pago"
        or doc.owner_id != payment_id
    ):
        raise HTTPException(404, "Documento no encontrado")
    key = doc.data.get("storage_key", "")
    if len(key) != 32 or any(char not in "0123456789abcdef" for char in key):
        raise HTTPException(404, "Archivo no disponible")
    path = STORAGE / key
    if not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, filename=doc.data.get("nombre", "archivo"), media_type="application/octet-stream")
