import os
import re
from pathlib import Path
from uuid import uuid4

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.records import admin_or_operator, build_resource_router
from app.core.database import get_db
from app.models.entities import Document, User
from app.models.cargas.cargas import LoadStage
from app.models.entities import (
    Client,
    Driver,
    Expense,
    Fueling,
    Load,
    Maintenance,
    Payment,
    Trip,
    Vehicle,
)

router = APIRouter()
STORAGE = Path(
    os.environ.get(
        "DOCUMENTOS_STORAGE_DIR",
        str(Path(__file__).resolve().parents[5] / "storage" / "documentos"),
    )
)
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024
FOLDER_LABELS = {
    "carga": "Cargas",
    "cliente": "Clientes",
    "conductor": "Conductores",
    "combustible": "Combustible",
    "gasto": "Gastos",
    "mantenimiento": "Mantenimiento",
    "pago": "Pagos",
    "viaje": "Viajes",
    "vehiculo": "Vehículos",
}


def _storage_for(owner_type: str) -> Path:
    storage_by_owner = {
        "carga": ("CARGAS_STORAGE_DIR", "cargas"),
        "combustible": ("COMBUSTIBLE_STORAGE_DIR", "combustible"),
        "gasto": ("GASTOS_STORAGE_DIR", "gastos"),
        "pago": ("PAGOS_STORAGE_DIR", "pagos"),
    }
    if owner_type in {"vehiculo", "viaje"}:
        return STORAGE
    config = storage_by_owner.get(owner_type)
    if not config:
        raise HTTPException(404, "Archivo no disponible")
    environment_key, folder = config
    return Path(os.environ.get(environment_key, str(STORAGE.parent / folder)))


def _related_owners(db: Session, folder: str, owner_id: str) -> dict[str, set[str]]:
    owner_ids: dict[str, set[str]] = {folder: {owner_id}}
    if folder == "viaje":
        trip = db.get(Trip, owner_id)
        if not trip or trip.deleted_at:
            raise HTTPException(404, "Viaje no encontrado")
        trip_ids = {owner_id}
        load_ids = set(
            db.scalars(select(Load.id).where(Load.trip_id == owner_id, Load.deleted_at.is_(None)))
        )
        load_ids.update(
            db.scalars(
                select(LoadStage.id_carga).where(
                    LoadStage.id_viaje == owner_id, LoadStage.deleted_at.is_(None)
                )
            )
        )
        owner_ids["carga"] = load_ids
        owner_ids["gasto"] = set(
            db.scalars(select(Expense.id).where(Expense.trip_id == owner_id, Expense.deleted_at.is_(None)))
        )
        owner_ids["combustible"] = set(
            db.scalars(select(Fueling.id).where(Fueling.trip_id == owner_id, Fueling.deleted_at.is_(None)))
        )
    elif folder == "vehiculo":
        vehicle = db.get(Vehicle, owner_id)
        if not vehicle or vehicle.deleted_at:
            raise HTTPException(404, "Vehículo no encontrado")
        trip_ids = set(
            db.scalars(
                select(Trip.id).where(Trip.vehicle_id == owner_id, Trip.deleted_at.is_(None))
            )
        )
        load_ids = set(
            db.scalars(
                select(Load.id).where(
                    Load.deleted_at.is_(None),
                    or_(
                        Load.trip_id.in_(trip_ids) if trip_ids else False,
                        Load.id.in_(
                            select(LoadStage.id_carga).where(
                                LoadStage.id_viaje.in_(trip_ids) if trip_ids else False,
                                LoadStage.deleted_at.is_(None),
                            )
                        ),
                    ),
                )
            )
        )
        owner_ids.update(
            viaje=trip_ids,
            carga=load_ids,
            gasto=set(
                db.scalars(
                    select(Expense.id).where(
                        Expense.deleted_at.is_(None),
                        or_(
                            Expense.vehicle_id == owner_id,
                            Expense.trip_id.in_(trip_ids) if trip_ids else False,
                        ),
                    )
                )
            ),
            combustible=set(
                db.scalars(
                    select(Fueling.id).where(
                        Fueling.deleted_at.is_(None),
                        or_(
                            Fueling.vehicle_id == owner_id,
                            Fueling.trip_id.in_(trip_ids) if trip_ids else False,
                        ),
                    )
                )
            ),
            mantenimiento=set(
                db.scalars(
                    select(Maintenance.id).where(
                        Maintenance.vehicle_id == owner_id, Maintenance.deleted_at.is_(None)
                    )
                )
            ),
        )
    return owner_ids


def _owner_labels(db: Session, documents: list[Document]) -> dict[tuple[str, str], str]:
    ids_by_type: dict[str, set[str]] = {}
    for doc in documents:
        ids_by_type.setdefault(doc.owner_type, set()).add(doc.owner_id)
    models = {
        "vehiculo": (Vehicle, lambda item: " · ".join(filter(None, (item.fleet_code, item.plate)))),
        "viaje": (Trip, lambda item: item.code),
        "carga": (Load, lambda item: item.code),
        "cliente": (Client, lambda item: item.name),
        "conductor": (Driver, lambda item: item.name),
        "gasto": (Expense, lambda item: item.category),
        "combustible": (Fueling, lambda item: f"Odómetro {item.odometer}"),
        "mantenimiento": (Maintenance, lambda item: item.data.get("tipo", "Mantenimiento")),
        "pago": (Payment, lambda item: f"Pago {item.id[:8]}"),
    }
    labels = {}
    for owner_type, owner_ids in ids_by_type.items():
        model_and_label = models.get(owner_type)
        if not model_and_label:
            continue
        model, label_for = model_and_label
        rows = db.scalars(select(model).where(model.id.in_(owner_ids))).all()
        for item in rows:
            labels[(owner_type, item.id)] = label_for(item) or FOLDER_LABELS[owner_type]
    return labels


def _document_payload(doc: Document, labels: dict[tuple[str, str], str]):
    return {
        "id": doc.id,
        "nombre": doc.data.get("nombre", "Archivo"),
        "tipo": doc.document_type,
        "propietario_tipo": doc.owner_type,
        "propietario_id": doc.owner_id,
        "propietario_nombre": labels.get(
            (doc.owner_type, doc.owner_id), FOLDER_LABELS.get(doc.owner_type, "Documentos")
        ),
        "carpeta": FOLDER_LABELS.get(doc.owner_type, "Documentos"),
        "tamano": doc.data.get("tamano", 0),
        "fecha": doc.created_at,
        "descargable": bool(doc.data.get("storage_key")),
    }


@router.get("/documentos/biblioteca")
def document_library(
    carpeta: str = Query("todos", pattern="^(todos|vehiculo|viaje)$"),
    propietario_id: str | None = Query(None, min_length=1, max_length=36),
    q: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    conditions = [Document.deleted_at.is_(None), Document.data["storage_key"].as_string().is_not(None)]
    if carpeta in {"vehiculo", "viaje"}:
        if propietario_id:
            related = _related_owners(db, carpeta, propietario_id)
            conditions.append(
                or_(
                    *[
                        and_(Document.owner_type == owner_type, Document.owner_id.in_(owner_ids))
                        for owner_type, owner_ids in related.items()
                        if owner_ids
                    ]
                )
            )
        else:
            conditions.append(Document.owner_type == carpeta)
    documents = db.scalars(
        select(Document).where(*conditions).order_by(Document.created_at.desc(), Document.id.desc())
    ).all()
    labels = _owner_labels(db, documents)
    if q:
        needle = q.casefold()
        documents = [
            doc
            for doc in documents
            if needle in str(doc.data.get("nombre", "")).casefold()
            or needle in doc.document_type.casefold()
            or needle in FOLDER_LABELS.get(doc.owner_type, "").casefold()
            or needle in labels.get((doc.owner_type, doc.owner_id), "").casefold()
        ]
    return [_document_payload(doc, labels) for doc in documents]


@router.post("/documentos/biblioteca", status_code=201)
async def upload_library_document(
    propietario_tipo: str,
    propietario_id: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    models = {"vehiculo": Vehicle, "viaje": Trip}
    model = models.get(propietario_tipo)
    if not model:
        raise HTTPException(422, "Selecciona una carpeta de vehículo o viaje")
    owner = db.get(model, propietario_id)
    if not owner or owner.deleted_at:
        raise HTTPException(404, "Registro no encontrado")
    name = Path((archivo.filename or "archivo").replace(chr(92), "/")).name
    if Path(name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, "Formato de archivo no permitido")
    STORAGE.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex
    path = STORAGE / key
    size = 0
    try:
        with path.open("xb") as stream:
            while chunk := await archivo.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(413, "El archivo supera 10 MB")
                stream.write(chunk)
        if size == 0:
            raise HTTPException(422, "El archivo está vacío")
        doc = Document(
            owner_type=propietario_tipo,
            owner_id=propietario_id,
            document_type=f"archivo_{propietario_tipo}",
            created_by=user.id,
            data={"nombre": name, "storage_key": key, "tamano": size},
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return _document_payload(doc, _owner_labels(db, [doc]))
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    finally:
        await archivo.close()


@router.get("/documentos/biblioteca/{document_id}/archivo")
def download_library_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    doc = db.get(Document, document_id)
    key = doc.data.get("storage_key", "") if doc and not doc.deleted_at else ""
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise HTTPException(404, "Documento no encontrado")
    path = _storage_for(doc.owner_type) / key
    if not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, filename=doc.data.get("nombre", "archivo"))


@router.get("/documentos/por-vencer")
def expiring_documents(
    dias: int = Query(30, ge=0, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=dias)
    items = db.scalars(
        select(Document).where(
            Document.deleted_at.is_(None), Document.expires_at >= now, Document.expires_at <= end
        )
    ).all()
    return [
        {
            "id": item.id,
            "tipo": item.document_type,
            "propietario_tipo": item.owner_type,
            "propietario_id": item.owner_id,
            "vence_en": item.expires_at,
            "data": item.data,
        }
        for item in items
    ]


router.include_router(build_resource_router("documentos"))
