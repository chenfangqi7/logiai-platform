from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import LogisticsException


class ExceptionRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def get(self, exception_id: str) -> LogisticsException | None:
        return await self.session.scalar(select(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.id == exception_id))

    async def by_rule(self, shipment_id: str, rule_code: str) -> LogisticsException | None:
        return await self.session.scalar(select(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.shipment_id == shipment_id, LogisticsException.rule_code == rule_code))

    async def list(self, status: str = "", level: str = "", type: str = "", offset: int = 0, limit: int = 50, since: datetime | None = None) -> tuple[int, list[LogisticsException]]:
        query = select(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id)
        if since:
            query = query.where(LogisticsException.detected_at >= since)
        if status:
            query = query.where(LogisticsException.status == status)
        if level:
            query = query.where(LogisticsException.level == level)
        if type:
            query = query.where(LogisticsException.type == type)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = list((await self.session.scalars(query.order_by(LogisticsException.detected_at.desc()).offset(offset).limit(limit))).all())
        return total, items
