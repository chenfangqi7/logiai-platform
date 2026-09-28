from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.auth import AuthenticatedUser
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def dashboard(session: AsyncSession, current: AuthenticatedUser) -> DashboardService:
    return DashboardService(session, current.user.tenant_id)


@router.get("/overview")
async def overview(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await dashboard(session, current).overview()


@router.get("/exception-trend")
async def exception_trend(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await dashboard(session, current).trend()


@router.get("/route-ranking")
async def route_ranking(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await dashboard(session, current).route_ranking()


@router.get("/ai-summary")
async def ai_summary(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await dashboard(session, current).summary()
