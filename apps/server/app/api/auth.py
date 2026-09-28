from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.auth import AuthService, AuthenticatedUser

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_session)]) -> TokenResponse:
    token = await AuthService(session).login(payload.tenant_code, payload.username, payload.password)
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=CurrentUserResponse)
async def me(current: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> CurrentUserResponse:
    user = current.user
    return CurrentUserResponse(id=user.id, tenant_id=user.tenant_id, tenant_code=current.tenant_code, username=user.username, email=user.email, role=user.role)
