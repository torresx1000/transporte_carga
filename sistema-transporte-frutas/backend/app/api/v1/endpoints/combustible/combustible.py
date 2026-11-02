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
from app.models.entities import Document, Fueling, User

router = build_resource_router("combustible")
STORAGE = Path(
    os.environ.get(
        "COMBUSTIBLE_STORAGE_DIR",
        str(Path(__file__).resolve().parents[5] / "storage" / "combustible"),
    )
)
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".xlsx"}
access = require_roles("admin", "operador")


@router.get("/{fueling_id}/documentos")
def fueling_documents(
    fueling_id: str, db: Session = Depends(get_db), user: User = Depends(access)
):
    fueling = db.get(Fueling, fueling_id)
    if not fueling or fueling.deleted_at:
        raise HTTPException(404, "Registro de combustible no encontrado")
    docs = db.scalars(
        select(Document).where(
            Document.owner_type == "combustible",
            Document.owner_id == fueling_id,
            Document.deleted_at.is_(None),
        )
    ).all()
    return [
        {"id": doc.id, "nombre": doc.data.get("nombre"), "tamano": doc.data.get("tamano")}
        for doc in docs
    ]


@router.post("/{fueling_id}/documentos", status_code=201)
async def upload_fueling_document(
    fueling_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(access),
):
    fueling = db.get(Fueling, fueling_id)
    if not fueling or fueling.deleted_at:
        raise HTTPException(404, "Registro de combustible no encontrado")
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
            owner_type="combustible",
            owner_id=fueling_id,
            document_type="comprobante_combustible",
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


@router.get("/{fueling_id}/documentos/{document_id}/archivo")
def download_fueling_document(
    fueling_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(access),
):
    fueling = db.get(Fueling, fueling_id)
    doc = db.get(Document, document_id)
    if (
        not fueling
        or fueling.deleted_at
        or not doc
        or doc.deleted_at
        or doc.owner_type != "combustible"
        or doc.owner_id != fueling_id
    ):
        raise HTTPException(404, "Documento no encontrado")
    key = doc.data.get("storage_key", "")
    if len(key) != 32 or any(char not in "0123456789abcdef" for char in key):
        raise HTTPException(404, "Archivo no disponible")
    path = STORAGE / key
    if not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(
        path,
        filename=doc.data.get("nombre", "archivo"),
        media_type="application/octet-stream",
    )
