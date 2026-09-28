from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.ai_usage import AIUsageService
from app.services.assistant import AssistantService
from app.services.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


def assistant(session: AsyncSession, current: AuthenticatedUser) -> AssistantService:
    return AssistantService(session, current.user.tenant_id, current.user.id)


def usage_service(session: AsyncSession, current: AuthenticatedUser) -> AIUsageService:
    return AIUsageService(session, current.user.tenant_id)


@router.post("/chat")
async def chat(payload: ChatInput, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    try:
        return await assistant(session, current).chat(payload.message, payload.conversation_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/conversations")
async def conversations(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await assistant(session, current).conversations()


@router.get("/conversations/{conversation_id}")
async def conversation(conversation_id: str, session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    result = await assistant(session, current).conversation(conversation_id)
    if result is None:
        raise HTTPException(404, "Conversation not found")
    return result


@router.get("/usage/dashboard")
async def usage_dashboard(session: Annotated[AsyncSession, Depends(get_session)], current: Annotated[AuthenticatedUser, Depends(get_current_user)]):
    return await usage_service(session, current).dashboard()


@router.get("/usage/logs")
async def usage_logs(
    session: Annotated[AsyncSession, Depends(get_session)],
    current: Annotated[AuthenticatedUser, Depends(get_current_user)],
    offset: int = 0,
    limit: int = 50,
):
    return await usage_service(session, current).logs(offset=offset, limit=limit)

