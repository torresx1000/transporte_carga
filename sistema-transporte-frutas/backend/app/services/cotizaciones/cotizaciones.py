from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.entities import Client, Quotation, QuotationItem, Route
from app.models.enums import QuotationStatus
from app.repositories.records import RecordRepository
from app.schemas.cotizaciones.cotizaciones import (
    CotizacionCreate,
    CotizacionLineaInput,
    CotizacionLineaResponse,
    CotizacionResponse,
    CotizacionUpdate,
)


def _money(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class CotizacionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RecordRepository(db, Quotation)

    def _response(self, item: Quotation) -> CotizacionResponse:
        lines = self.db.scalars(
            select(QuotationItem)
            .where(
                QuotationItem.quotation_id == item.id,
                QuotationItem.deleted_at.is_(None),
            )
            .order_by(QuotationItem.line_order, QuotationItem.id)
        ).all()
        return CotizacionResponse(
            id=item.id,
            codigo=item.code,
            cliente_id=item.client_id,
            ruta_id=item.route_id,
            estado=item.status,
            fecha_emision=item.issue_date,
            valida_hasta=item.valid_until,
            moneda=item.currency,
            descuento_tasa_bps=item.discount_rate_bps,
            descuento_centimos=item.discount_minor,
            impuesto_tasa_bps=item.tax_rate_bps,
            subtotal_centimos=item.subtotal,
            impuesto_centimos=item.tax,
            total_centimos=item.total,
            lineas=[
                CotizacionLineaResponse(
                    descripcion=line.description,
                    cantidad=line.quantity,
                    precio_unitario_centimos=line.unit_price_cents,
                    orden=line.line_order,
                    importe_centimos=_money(
                        Decimal(line.quantity) * Decimal(line.unit_price_cents)
                    ),
                )
                for line in lines
            ],
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by=item.created_by,
        )

    @staticmethod
    def _calc(lines: list[CotizacionLineaInput], discount_bps: int, tax_bps: int):
        subtotal = sum(
            _money(Decimal(line.cantidad) * Decimal(line.precio_unitario_centimos))
            for line in lines
        )
        discount = _money(Decimal(subtotal) * Decimal(discount_bps) / Decimal(10000))
        taxable = subtotal - discount
        tax = _money(Decimal(taxable) * Decimal(tax_bps) / Decimal(10000))
        return subtotal, discount, tax, taxable + tax

    def list(self, page: int, page_size: int, q: str | None, **filters):
        mapped = {
            key: (column, filters[key])
            for key, column in (
                ("estado", "status"),
                ("cliente_id", "client_id"),
                ("ruta_id", "route_id"),
            )
            if filters.get(key) not in (None, "")
        }
        total, rows = self.repo.list_configured(page, page_size, q, ("code",), mapped)
        return {
            "items": [self._response(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    def get(self, record_id: str):
        item = self.repo.get(record_id)
        if item is None:
            raise ApiError(404, "QUOTATION_NOT_FOUND", "Cotización no encontrada.")
        return self._response(item)

    def _validate_refs(self, client_id: str, route_id: str):
        client, route = self.db.get(Client, client_id), self.db.get(Route, route_id)
        if (
            client is None
            or client.deleted_at is not None
            or client.status not in {"activo", "activa"}
        ):
            raise ApiError(
                409,
                "QUOTATION_CLIENT_INACTIVE",
                "El cliente no existe o está inactivo.",
                {"field": "cliente_id"},
            )
        if (
            route is None
            or route.deleted_at is not None
            or route.status not in {"activa", "activo", "active"}
        ):
            raise ApiError(
                409,
                "QUOTATION_ROUTE_INACTIVE",
                "La ruta no existe o está inactiva.",
                {"field": "ruta_id"},
            )

    def _replace_lines(self, item: Quotation, lines: list[CotizacionLineaInput], user_id: str):
        existing = self.db.scalars(
            select(QuotationItem).where(QuotationItem.quotation_id == item.id)
        ).all()
        for line in existing:
            self.db.delete(line)
        for line in lines:
            self.db.add(
                QuotationItem(
                    quotation_id=item.id,
                    description=line.descripcion,
                    quantity=line.cantidad,
                    unit_price_cents=line.precio_unitario_centimos,
                    line_order=line.orden,
                    created_by=user_id,
                    data={},
                )
            )

    def create(self, payload: CotizacionCreate, created_by: str):
        self._validate_refs(payload.cliente_id, payload.ruta_id)
        subtotal, discount, tax, total = self._calc(
            payload.lineas, payload.descuento_tasa_bps, payload.impuesto_tasa_bps
        )
        item = Quotation(
            code=payload.codigo or f"COT-{uuid4().hex[:12].upper()}",
            client_id=payload.cliente_id,
            route_id=payload.ruta_id,
            status=QuotationStatus(payload.estado),
            issue_date=payload.fecha_emision,
            valid_until=payload.valida_hasta,
            currency="PEN",
            discount_rate_bps=payload.descuento_tasa_bps,
            discount_minor=discount,
            tax_rate_bps=payload.impuesto_tasa_bps,
            subtotal=subtotal,
            tax=tax,
            total=total,
            created_by=created_by,
            data={},
        )
        self.db.add(item)
        try:
            self.db.flush()
            self._replace_lines(item, payload.lineas, created_by)
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise ApiError(
                409,
                "QUOTATION_DUPLICATE",
                "Ya existe una cotización con ese código.",
                {"field": "codigo"},
            ) from None
        return self._response(item)

    def update(self, record_id: str, payload: CotizacionUpdate):
        item = self.repo.get(record_id)
        if item is None:
            raise ApiError(404, "QUOTATION_NOT_FOUND", "Cotización no encontrada.")
        changes = payload.model_dump(exclude_unset=True)
        state = changes.get("estado", item.status)
        allowed = {"borrador", "enviada", "aprobada", "rechazada", "convertida_a_carga"}
        if state not in allowed:
            raise ApiError(
                422,
                "QUOTATION_INVALID_STATUS",
                "Estado de cotización no permitido.",
                {"field": "estado"},
            )
        issue = changes.get("fecha_emision", item.issue_date)
        valid = changes.get("valida_hasta", item.valid_until)
        if valid <= issue:
            raise ApiError(
                422,
                "QUOTATION_INVALID_VALIDITY",
                "La vigencia debe ser posterior a la emisión.",
                {"field": "valida_hasta"},
            )
        current_lines = self.db.scalars(
            select(QuotationItem)
            .where(QuotationItem.quotation_id == item.id)
            .order_by(QuotationItem.line_order)
        ).all()
        lines = changes.get("lineas")
        if lines is None:
            lines = [
                CotizacionLineaInput(
                    descripcion=line.description,
                    cantidad=line.quantity,
                    precio_unitario_centimos=line.unit_price_cents,
                    orden=line.line_order,
                )
                for line in current_lines
            ]
        discount_rate = changes.get("descuento_tasa_bps", item.discount_rate_bps)
        tax_rate = changes.get("impuesto_tasa_bps", item.tax_rate_bps)
        subtotal, discount, tax, total = self._calc(lines, discount_rate, tax_rate)
        item.status = QuotationStatus(state)
        item.issue_date, item.valid_until = issue, valid
        item.discount_rate_bps, item.tax_rate_bps = discount_rate, tax_rate
        item.subtotal, item.discount_minor, item.tax, item.total = subtotal, discount, tax, total
        if "lineas" in changes:
            self._replace_lines(item, lines, item.created_by or "")
        try:
            self.db.commit()
            self.db.refresh(item)
        except IntegrityError:
            self.db.rollback()
            raise ApiError(
                409, "QUOTATION_CONFLICT", "No se pudo actualizar la cotización."
            ) from None
        return self._response(item)

    def delete(self, record_id: str):
        item = self.repo.get(record_id)
        if item is None:
            raise ApiError(404, "QUOTATION_NOT_FOUND", "Cotización no encontrada.")
        self.repo.delete(item)
