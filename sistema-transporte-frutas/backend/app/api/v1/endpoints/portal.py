from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.entities import User
from app.repositories.portal import PortalRepository
from app.services.portal import PortalService
from app.schemas.responses import (
    PortalDocumentResponse,
    PortalLoadResponse,
    PortalPaymentResponse,
    PortalProfileResponse,
    PortalTripResponse,
)

router = APIRouter(prefix="/portal", tags=["portal"])


require_client = require_roles("cliente")


def get_portal_service(db: Session = Depends(get_db)) -> PortalService:
    return PortalService(PortalRepository(db))


@router.get("/me", response_model=PortalProfileResponse)
def portal_profile(user: User = Depends(require_client)):
    return {
        "id": user.id,
        "email": user.email,
        "cliente_id": user.data.get("client_id"),
        "nombre": user.data.get("name"),
    }


@router.get("/cargas", response_model=list[PortalLoadResponse])
def portal_loads(
    user: User = Depends(require_client), service: PortalService = Depends(get_portal_service)
):
    return service.loads(user)


@router.get("/cargas/{load_id}", response_model=PortalLoadResponse)
def portal_load(
    load_id: str,
    user: User = Depends(require_client),
    service: PortalService = Depends(get_portal_service),
):
    return service.load(user, load_id)


@router.get("/viajes", response_model=list[PortalTripResponse])
def portal_trips(
    user: User = Depends(require_client), service: PortalService = Depends(get_portal_service)
):
    return service.trips(user)


@router.get("/viajes/{trip_id}", response_model=PortalTripResponse)
def portal_trip(
    trip_id: str,
    user: User = Depends(require_client),
    service: PortalService = Depends(get_portal_service),
):
    return service.trip(user, trip_id)


@router.get("/documentos", response_model=list[PortalDocumentResponse])
def portal_documents(
    user: User = Depends(require_client), service: PortalService = Depends(get_portal_service)
):
    return service.documents(user)


@router.get("/documentos/{document_id}", response_model=PortalDocumentResponse)
def portal_document(
    document_id: str,
    user: User = Depends(require_client),
    service: PortalService = Depends(get_portal_service),
):
    return service.document(user, document_id)


@router.get("/pagos", response_model=list[PortalPaymentResponse])
def portal_payments(
    user: User = Depends(require_client), service: PortalService = Depends(get_portal_service)
):
    return service.payments(user)


@router.get("/pagos/{payment_id}", response_model=PortalPaymentResponse)
def portal_payment(
    payment_id: str,
    user: User = Depends(require_client),
    service: PortalService = Depends(get_portal_service),
):
    return service.payment(user, payment_id)
