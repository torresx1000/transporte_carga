from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.records import admin_or_operator, build_resource_router
from app.core.database import get_db
from app.core.permissions import require_roles
from app.models.entities import (
    Client,
    Load,
    ReturnAllocation,
    ReturnBalanceCut,
    ReturnRecord,
    User,
)
from app.schemas.responses import CrateBalanceResponse, ReturnBalanceCutResponse

router = APIRouter()


def _period_condition(column, period_id: str | None):
    return column.is_(None) if period_id is None else column == period_id


def _active_cut(db: Session, client_id: str) -> ReturnBalanceCut | None:
    return db.scalar(
        select(ReturnBalanceCut)
        .where(ReturnBalanceCut.client_id == client_id)
        .order_by(ReturnBalanceCut.sequence.desc())
        .limit(1)
    )


def _period_totals(db: Session, client_id: str, period_id: str | None) -> tuple[int, int]:
    dispatched = db.scalar(
        select(func.sum(Load.jabas_dispatched)).where(
            Load.client_id == client_id,
            Load.deleted_at.is_(None),
            _period_condition(Load.balance_period_id, period_id),
        )
    ) or 0
    allocations = db.scalar(
        select(func.sum(ReturnAllocation.returned_total)).where(
            ReturnAllocation.client_id == client_id,
            ReturnAllocation.deleted_at.is_(None),
            _period_condition(ReturnAllocation.balance_period_id, period_id),
        )
    ) or 0
    legacy_returns = db.scalar(
        select(func.sum(ReturnRecord.returned_total)).where(
            ReturnRecord.client_id == client_id,
            ReturnRecord.deleted_at.is_(None),
            _period_condition(ReturnRecord.balance_period_id, period_id),
            ~select(ReturnAllocation.id)
            .where(ReturnAllocation.return_id == ReturnRecord.id)
            .exists(),
        )
    ) or 0
    return int(dispatched), int(allocations + legacy_returns)


@router.get(
    "/retornos/saldos-por-cliente",
    response_model=list[CrateBalanceResponse],
)
def return_balances(db: Session = Depends(get_db), user: User = Depends(admin_or_operator)):
    cuts = db.scalars(
        select(ReturnBalanceCut).order_by(
            ReturnBalanceCut.created_at.desc(), ReturnBalanceCut.sequence.desc()
        )
    ).all()
    latest_cut_by_client: dict[str, ReturnBalanceCut] = {}
    for cut in cuts:
        latest_cut_by_client.setdefault(cut.client_id, cut)

    dispatched_rows = db.execute(
        select(Load.client_id, Load.balance_period_id, func.sum(Load.jabas_dispatched))
        .where(Load.deleted_at.is_(None), Load.client_id.is_not(None))
        .group_by(Load.client_id, Load.balance_period_id)
    ).all()
    dispatched = {
        (client_id, period_id): int(total or 0)
        for client_id, period_id, total in dispatched_rows
    }

    allocation_rows = db.execute(
        select(
            ReturnAllocation.client_id,
            ReturnAllocation.balance_period_id,
            func.sum(ReturnAllocation.returned_total),
        )
        .where(ReturnAllocation.deleted_at.is_(None))
        .group_by(ReturnAllocation.client_id, ReturnAllocation.balance_period_id)
    ).all()
    returned = {
        (client_id, period_id): int(total or 0)
        for client_id, period_id, total in allocation_rows
    }

    legacy_rows = db.execute(
        select(
            ReturnRecord.client_id,
            ReturnRecord.balance_period_id,
            func.sum(ReturnRecord.returned_total),
        )
        .where(
            ReturnRecord.deleted_at.is_(None),
            ~select(ReturnAllocation.id)
            .where(ReturnAllocation.return_id == ReturnRecord.id)
            .exists(),
        )
        .group_by(ReturnRecord.client_id, ReturnRecord.balance_period_id)
    ).all()
    for client_id, period_id, total in legacy_rows:
        key = (client_id, period_id)
        returned[key] = returned.get(key, 0) + int(total or 0)

    client_ids = (
        {client_id for client_id, _period_id in dispatched}
        | {client_id for client_id, _period_id in returned}
        | set(latest_cut_by_client)
    )
    balances = []
    for client_id in client_ids:
        period_id = latest_cut_by_client.get(client_id)
        active_period_id = period_id.id if period_id else None
        dispatched_total = dispatched.get((client_id, active_period_id), 0)
        returned_total = returned.get((client_id, active_period_id), 0)
        balances.append(
            {
                "cliente_id": client_id,
                "total_despachadas": dispatched_total,
                "total_retornadas": returned_total,
                "saldo_pendiente": dispatched_total - returned_total,
                "periodo_id": active_period_id,
            }
        )
    return balances


@router.get(
    "/retornos/historial-cortes",
    response_model=list[ReturnBalanceCutResponse],
)
def return_balance_cut_history(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(admin_or_operator),
):
    cuts = db.scalars(
        select(ReturnBalanceCut)
        .order_by(ReturnBalanceCut.created_at.desc(), ReturnBalanceCut.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": cut.id,
            "cliente_id": cut.client_id,
            "numero_corte": cut.sequence,
            "cliente_nombre": cut.client_name,
            "total_despachadas": cut.dispatched_total,
            "total_retornadas": cut.returned_total,
            "saldo_pendiente": cut.dispatched_total - cut.returned_total,
            "fecha": cut.created_at,
            "usuario_email": cut.actor_email,
        }
        for cut in cuts
    ]


@router.post(
    "/retornos/clientes/{client_id}/reiniciar-saldo",
    response_model=ReturnBalanceCutResponse,
    status_code=201,
)
def reset_return_balance(
    client_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    client = db.scalar(
        select(Client)
        .where(Client.id == client_id, Client.deleted_at.is_(None))
        .with_for_update()
    )
    if not client:
        raise HTTPException(404, "Cliente no encontrado")

    active_cut = _active_cut(db, client_id)
    dispatched_total, returned_total = _period_totals(
        db, client_id, active_cut.id if active_cut else None
    )
    sequence = (
        db.scalar(
            select(func.max(ReturnBalanceCut.sequence)).where(
                ReturnBalanceCut.client_id == client_id
            )
        )
        or 0
    ) + 1
    cut = ReturnBalanceCut(
        id=str(uuid4()),
        client_id=client.id,
        sequence=sequence,
        client_name=client.name,
        dispatched_total=dispatched_total,
        returned_total=returned_total,
        created_by=user.id,
        actor_email=user.email,
    )
    db.add(cut)
    db.commit()
    db.refresh(cut)
    return {
        "id": cut.id,
        "cliente_id": cut.client_id,
        "numero_corte": cut.sequence,
        "cliente_nombre": cut.client_name,
        "total_despachadas": cut.dispatched_total,
        "total_retornadas": cut.returned_total,
        "saldo_pendiente": cut.dispatched_total - cut.returned_total,
        "fecha": cut.created_at,
        "usuario_email": cut.actor_email,
    }


router.include_router(build_resource_router("retornos"))
