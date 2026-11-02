from app.schemas.cargas.cargas import PlanEtapas, EtapaEstado
from app.services.etapas.etapas import EtapasService
from pathlib import Path
from uuid import uuid4
import os
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.models.entities import Document, Load
from sqlalchemy import select
from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.endpoints.records import ResourceContract, build_resource_router
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.entities import User
from app.schemas.cargas.cargas import CargaCreate, CargaEstadoUpdate, CargaResponse, CargaUpdate
from app.services.cargas.cargas import CargaService


router = build_resource_router(
    "cargas",
    ResourceContract(
        create_schema=CargaCreate,
        update_schema=CargaUpdate,
        response_schema=CargaResponse,
        search_fields=("code", "product", "variety", "origin", "destination"),
        filters={"estado": "status", "cliente_id": "client_id", "viaje_id": "trip_id"},
        unique_fields={"codigo": "code"},
        column_fields={
            "codigo": "code",
            "cliente_id": "client_id",
            "viaje_id": "trip_id",
            "estado": "status",
            "prioridad": "priority",
            "jabas_despachadas": "jabas_dispatched",
            "producto": "product",
            "variedad": "variety",
            "cantidad": "quantity",
            "unidad": "unit",
            "peso_neto_total_kg": "net_weight_kg",
            "peso_bruto_total_kg": "gross_weight_kg",
            "procedencia": "origin",
            "destino": "destination",
            "fecha_recojo": "pickup_date",
            "fecha_entrega": "delivery_date",
            "monto_cobrar_centimos": "charge_amount_minor",
            "moneda": "currency",
        },
        permissions={
            "list": ("admin", "operador"),
            "read": ("admin", "operador"),
            "create": ("admin", "operador"),
            "update": ("admin", "operador"),
            "delete": ("admin",),
        },
        service_factory=CargaService,
        update_actor_context=True,
        prefix="/cargas",
    ),
)


@router.post("/{load_id}/estado", response_model=CargaResponse)
def transition_load(
    load_id: str,
    payload: CargaEstadoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    return CargaService(db).transition(load_id, payload)


@router.get("/{load_id}/etapas")
def load_stages(
    load_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    CargaService(db).get(load_id)
    service = EtapasService(db)
    return [service.serialize(row) for row in service.stages(load_id=load_id)]


@router.put("/{load_id}/etapas")
def plan_load(
    load_id: str,
    payload: PlanEtapas,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    return EtapasService(db).plan(load_id, payload.etapas, user.id)


@router.get("/{load_id}/viajes-compatibles")
def compatible_trips(
    load_id: str,
    origen_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    return EtapasService(db).compatible(load_id, origen_id)


@router.post("/{load_id}/etapas/{stage_id}/estado")
def transition_stage(
    load_id: str,
    stage_id: str,
    payload: EtapaEstado,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    return EtapasService(db).transition(load_id, stage_id, payload.estado)


STORAGE = Path(
    os.environ.get(
        "CARGAS_STORAGE_DIR", str(Path(__file__).resolve().parents[5] / "storage" / "cargas")
    )
)


@router.get("/{load_id}/documentos")
def load_documents(
    load_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    CargaService(db).get(load_id)
    return [
        {
            "id": d.id,
            "nombre": d.data.get("nombre"),
            "tipo": d.document_type,
            "tamano": d.data.get("tamano"),
        }
        for d in db.scalars(
            select(Document).where(
                Document.owner_type == "carga",
                Document.owner_id == load_id,
                Document.deleted_at.is_(None),
            )
        ).all()
    ]


@router.post("/{load_id}/documentos", status_code=201)
async def upload_load_document(
    load_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador")),
):
    CargaService(db).get(load_id)
    name = Path((archivo.filename or "archivo").replace(chr(92), "/")).name
    if Path(name).suffix.lower() not in {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".docx",
        ".xlsx",
    }:
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
            owner_type="carga",
            owner_id=load_id,
            document_type="archivo_carga",
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


@router.get("/{load_id}/documentos/{document_id}/archivo")
def download_load_document(
    load_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "operador", "cliente")),
):
    load = db.get(Load, load_id)
    if (
        not load
        or load.deleted_at
        or (user.role == "cliente" and user.data.get("client_id") != load.client_id)
    ):
        raise HTTPException(404, "Documento no encontrado")
    doc = db.get(Document, document_id)
    if not doc or doc.deleted_at or doc.owner_type != "carga" or doc.owner_id != load_id:
        raise HTTPException(404, "Documento no encontrado")
    key = doc.data.get("storage_key", "")
    if len(key) != 32 or any(c not in "0123456789abcdef" for c in key):
        raise HTTPException(404, "Archivo no disponible")
    path = STORAGE / key
    if not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(
        path, filename=doc.data.get("nombre", "archivo"), media_type="application/octet-stream"
    )
