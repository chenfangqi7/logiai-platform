from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.services.auth import AuthService, AuthenticatedUser

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthenticatedUser:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing credentials", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise invalid
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError:
        raise invalid from None
    current = await AuthService(session).current_user(claims["tenant_id"], claims["sub"])
    if current is None:
        raise invalid
    return current
