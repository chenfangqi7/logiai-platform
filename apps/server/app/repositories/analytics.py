from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import LogisticsException, Route, Shipment


class AnalyticsRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def overview(self, since: datetime) -> dict[str, int]:
        shipments_today = await self.session.scalar(select(func.count()).select_from(Shipment).where(Shipment.tenant_id == self.tenant_id, Shipment.created_at >= since)) or 0
        in_transit = await self.session.scalar(select(func.count()).select_from(Shipment).where(Shipment.tenant_id == self.tenant_id, Shipment.status == "IN_TRANSIT")) or 0
        open_exceptions = await self.session.scalar(select(func.count()).select_from(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.status == "open")) or 0
        high_risk = await self.session.scalar(select(func.count()).select_from(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.status == "open", LogisticsException.level.in_(["HIGH", "CRITICAL"]))) or 0
        return {"shipments_today": shipments_today, "in_transit": in_transit, "exception_count": open_exceptions, "high_risk_count": high_risk}

    async def daily_exception_count(self, start: datetime, end: datetime) -> int:
        return await self.session.scalar(select(func.count()).select_from(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.detected_at >= start, LogisticsException.detected_at < end)) or 0

    async def today_exception_stats(self, start: datetime) -> dict[str, int]:
        base = [LogisticsException.tenant_id == self.tenant_id, LogisticsException.detected_at >= start]
        count = await self.session.scalar(select(func.count()).select_from(LogisticsException).where(*base)) or 0
        shipments = await self.session.scalar(select(func.count(func.distinct(LogisticsException.shipment_id))).where(*base)) or 0
        high = await self.session.scalar(select(func.count()).select_from(LogisticsException).where(*base, LogisticsException.level.in_(["HIGH", "CRITICAL"]))) or 0
        return {"exception_count": count, "shipment_count": shipments, "high_risk_count": high}

    async def type_distribution(self) -> list[dict]:
        rows = (await self.session.execute(select(LogisticsException.type, func.count()).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.status == "open").group_by(LogisticsException.type))).all()
        return [{"type": kind, "count": count} for kind, count in rows]

    async def route_ranking(self, limit: int = 10) -> list[dict]:
        query = (
            select(Route.id, Route.name, func.count(LogisticsException.id).label("exception_count"))
            .join(Shipment, (Shipment.route_id == Route.id) & (Shipment.tenant_id == self.tenant_id))
            .join(LogisticsException, (LogisticsException.shipment_id == Shipment.id) & (LogisticsException.tenant_id == self.tenant_id))
            .where(Route.tenant_id == self.tenant_id, LogisticsException.status == "open")
            .group_by(Route.id, Route.name).order_by(func.count(LogisticsException.id).desc()).limit(limit)
        )
        return [{"route_id": route_id, "route_name": name, "exception_count": count} for route_id, name, count in (await self.session.execute(query)).all()]

    async def route_exception_types(self, route_id: str, since: datetime) -> list[dict]:
        query = (
            select(LogisticsException.type, func.count())
            .join(Shipment, (Shipment.id == LogisticsException.shipment_id) & (Shipment.tenant_id == self.tenant_id))
            .where(LogisticsException.tenant_id == self.tenant_id, Shipment.route_id == route_id, LogisticsException.detected_at >= since)
            .group_by(LogisticsException.type)
        )
        return [{"type": kind, "count": count} for kind, count in (await self.session.execute(query)).all()]

    async def recent_exceptions(self, limit: int = 8) -> list[LogisticsException]:
        return list((await self.session.scalars(select(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id).order_by(LogisticsException.detected_at.desc()).limit(limit))).all())
