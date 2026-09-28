from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.auth import AuthRepository


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    tenant_code: str


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AuthRepository(session)

    async def login(self, tenant_code: str, username: str, password: str) -> str | None:
        tenant = await self.repository.get_tenant_by_code(tenant_code)
        if tenant is None:
            return None
        user = await self.repository.get_user_by_username(tenant.id, username)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return create_access_token(user.id, tenant.id)

    async def current_user(self, tenant_id: str, user_id: str) -> AuthenticatedUser | None:
        user = await self.repository.get_user_by_id(tenant_id, user_id)
        if user is None:
            return None
        # The tenant code is fetched under the same tenant scope as the user.
        from app.models.tenant import Tenant

        tenant = await self.repository.session.get(Tenant, tenant_id)
        if tenant is None:
            return None
        return AuthenticatedUser(user=user, tenant_code=tenant.code)
