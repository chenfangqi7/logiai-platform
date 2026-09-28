from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.auth import AuthenticatedUser
from app.services.common import serialize_model
from app.services.exceptions import ExceptionService
from app.services.exception_analysis import ExceptionAnalysisService

router = APIRouter(prefix="/api/v1/exceptions", tags=["exceptions"])


@router.get("")
async def list_exceptions(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)],
    status: str = "", level: str = "", type: str = "", offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    total, rows = await ExceptionService(session, current.user.tenant_id).repo.list(status, level, type, offset, limit)
    return {"total": total, "items": [serialize_model(item) for item in rows]}


@router.get("/{exception_id}")
async def get_exception(exception_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    item = await ExceptionService(session, current.user.tenant_id).repo.get(exception_id)
    if item is None:
        raise HTTPException(404, "Exception not found")
    return serialize_model(item)


@router.post("/{exception_id}/resolve")
async def resolve_exception(exception_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    svc = ExceptionService(session, current.user.tenant_id)
    item = await svc.repo.get(exception_id)
    if item is None:
        raise HTTPException(404, "Exception not found")
    return serialize_model(await svc.resolve(item))


@router.post("/{exception_id}/analyze")
async def analyze_exception(exception_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        item = await ExceptionAnalysisService(session, current.user.tenant_id).analyze(exception_id)
    except Exception as exc:
        raise HTTPException(502, "Model analysis failed") from exc
    if item is None:
        raise HTTPException(404, "Exception not found")
    return serialize_model(item)
