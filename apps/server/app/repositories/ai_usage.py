from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AIUsage


class AIUsageRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def summary(self, today_start: datetime) -> dict:
        total_stmt = select(
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens), 0),
            func.coalesce(func.sum(AIUsage.output_tokens), 0),
            func.coalesce(func.sum(AIUsage.cost), 0),
        ).where(AIUsage.tenant_id == self.tenant_id)
        total_row = (await self.session.execute(total_stmt)).one()

        today_stmt = select(
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens), 0),
            func.coalesce(func.sum(AIUsage.output_tokens), 0),
            func.coalesce(func.sum(AIUsage.cost), 0),
        ).where(AIUsage.tenant_id == self.tenant_id, AIUsage.created_at >= today_start)
        today_row = (await self.session.execute(today_stmt)).one()

        total_input = int(total_row[1])
        total_output = int(total_row[2])
        today_input = int(today_row[1])
        today_output = int(today_row[2])

        return {
            "total_calls": int(total_row[0]),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost": float(total_row[3]),
            "today_calls": int(today_row[0]),
            "today_input_tokens": today_input,
            "today_output_tokens": today_output,
            "today_tokens": today_input + today_output,
            "today_cost": float(today_row[3]),
        }

    async def trend(self, days: int = 7) -> list[dict]:
        tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(timezone.utc).astimezone(tz)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        items: list[dict] = []

        for offset in reversed(range(days)):
            start = today - timedelta(days=offset)
            end = start + timedelta(days=1)
            stmt = select(
                func.count(AIUsage.id),
                func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
                func.coalesce(func.sum(AIUsage.cost), 0),
            ).where(
                AIUsage.tenant_id == self.tenant_id,
                AIUsage.created_at >= start.astimezone(timezone.utc),
                AIUsage.created_at < end.astimezone(timezone.utc),
            )
            row = (await self.session.execute(stmt)).one()
            items.append({
                "date": start.strftime("%Y-%m-%d"),
                "calls": int(row[0]),
                "tokens": int(row[1]),
                "cost": float(row[2]),
            })
        return items

    async def distribution_by_purpose(self) -> list[dict]:
        stmt = select(
            AIUsage.purpose,
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
        ).where(AIUsage.tenant_id == self.tenant_id).group_by(AIUsage.purpose)
        rows = (await self.session.execute(stmt)).all()
        return [{"purpose": row[0], "calls": int(row[1]), "tokens": int(row[2])} for row in rows]

    async def distribution_by_model(self) -> list[dict]:
        stmt = select(
            func.coalesce(AIUsage.model, "unknown"),
            func.count(AIUsage.id),
            func.coalesce(func.sum(AIUsage.input_tokens + AIUsage.output_tokens), 0),
        ).where(AIUsage.tenant_id == self.tenant_id).group_by(AIUsage.model)
        rows = (await self.session.execute(stmt)).all()
        return [{"model": row[0], "calls": int(row[1]), "tokens": int(row[2])} for row in rows]

    async def logs(self, limit: int = 50, offset: int = 0) -> tuple[int, list[AIUsage]]:
        count_stmt = select(func.count(AIUsage.id)).where(AIUsage.tenant_id == self.tenant_id)
        total = await self.session.scalar(count_stmt) or 0
        list_stmt = (
            select(AIUsage)
            .where(AIUsage.tenant_id == self.tenant_id)
            .order_by(desc(AIUsage.created_at))
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.scalars(list_stmt)).all())
        return total, items
