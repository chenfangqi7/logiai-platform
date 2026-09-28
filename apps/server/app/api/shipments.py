from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.auth import AuthenticatedUser
from app.services.common import serialize_model
from app.services.shipments import ShipmentService

router = APIRouter(prefix="/api/v1/shipments", tags=["shipments"])


@router.get("")
async def list_shipments(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)],
    search: str = "", status: str = "", offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    svc = ShipmentService(session, current.user.tenant_id)
    total, rows = await svc.repo.shipments(search, status, offset, limit)
    return {"total": total, "items": [serialize_model(item) for item in rows]}


@router.get("/{shipment_id}")
async def get_shipment(shipment_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    detail = await ShipmentService(session, current.user.tenant_id).detail(shipment_id)
    if detail is None:
        raise HTTPException(404, "Shipment not found")
    return detail


@router.get("/{shipment_id}/tracking")
async def get_tracking(shipment_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = ShipmentService(session, current.user.tenant_id)
    if await svc.repo.shipment(shipment_id) is None:
        raise HTTPException(404, "Shipment not found")
    return [serialize_model(item) for item in await svc.repo.tracking(shipment_id)]


@router.get("/{shipment_id}/exceptions")
async def get_shipment_exceptions(shipment_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = ShipmentService(session, current.user.tenant_id)
    if await svc.repo.shipment(shipment_id) is None:
        raise HTTPException(404, "Shipment not found")
    return [serialize_model(item) for item in await svc.repo.exceptions_for_shipment(shipment_id)]
