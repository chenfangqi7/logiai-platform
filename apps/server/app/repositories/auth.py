from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_tenant_by_code(self, code: str) -> Tenant | None:
        return await self.session.scalar(select(Tenant).where(Tenant.code == code, Tenant.status == "active"))

    async def get_user_by_username(self, tenant_id: str, username: str) -> User | None:
        return await self.session.scalar(
            select(User).where(User.tenant_id == tenant_id, User.username == username, User.status == "active")
        )

    async def get_user_by_id(self, tenant_id: str, user_id: str) -> User | None:
        return await self.session.scalar(
            select(User).join(Tenant, Tenant.id == User.tenant_id).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.status == "active",
                Tenant.status == "active",
            )
        )
