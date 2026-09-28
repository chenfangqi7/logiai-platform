import hashlib
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway.provider import get_llm_provider, is_llm_configured
from app.core.config import get_settings
from app.models.domain import AIUsage
from app.repositories.analytics import AnalyticsRepository
from app.services.common import serialize_model


def china_day_start(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("Asia/Shanghai"))
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


class DashboardService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = AnalyticsRepository(session, tenant_id)

    async def overview(self) -> dict:
        counts = await self.repo.overview(china_day_start())
        counts["type_distribution"] = await self.repo.type_distribution()
        counts["recent_exceptions"] = [serialize_model(item) for item in await self.repo.recent_exceptions()]
        return counts

    async def trend(self, days: int = 7) -> list[dict]:
        today = china_day_start()
        result = []
        for offset in range(days - 1, -1, -1):
            start = today - timedelta(days=offset)
            result.append({"date": start.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat(),
                "count": await self.repo.daily_exception_count(start, start + timedelta(days=1))})
        return result

    async def route_ranking(self) -> list[dict]:
        return await self.repo.route_ranking()

    async def today_exception_stats(self) -> dict[str, int]:
        return await self.repo.today_exception_stats(china_day_start())

    async def route_issue_summary(self, route_keyword: str) -> dict | None:
        ranking = await self.repo.route_ranking(100)
        match = next((item for item in ranking if route_keyword in item["route_name"]), None)
        if match is None:
            return None
        return {**match, "today_types": await self.repo.route_exception_types(match["route_id"], china_day_start())}

    async def summary(self) -> dict[str, str]:
        counts = await self.repo.overview(china_day_start())
        ranking = await self.repo.route_ranking(3)
        if counts["exception_count"] == 0:
            fallback = "当前没有未处理异常。请继续关注在途运单和轨迹更新。"
        else:
            lines = [f"当前有 {counts['exception_count']} 条未处理异常，其中 {counts['high_risk_count']} 条为高风险。"]
            if ranking:
                top = ranking[0]
                lines.append(f"{top['route_name']} 线路异常最多，共 {top['exception_count']} 条，建议优先排查。")
            fallback = "\n".join(lines)
        settings = get_settings()
        if not is_llm_configured(settings):
            return {"summary": fallback, "provider": "rules"}
        evidence = {"counts": counts, "route_ranking": ranking}
        digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        cache_key = f"dashboard-summary:{self.tenant_id}:{digest}"
        redis = Redis.from_url(settings.redis_url)
        try:
            cached = await redis.get(cache_key)
            if cached:
                return {"summary": cached.decode(), "provider": "llm-cache"}
        except Exception:
            pass
        finally:
            await redis.aclose()
        try:
            generation = await get_llm_provider().generate(
                "你是物流运营分析助手。仅根据结构化统计撰写简短中文摘要，不编造事实或趋势。",
                json.dumps(evidence, ensure_ascii=False),
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            return {"summary": fallback, "provider": "rules"}
        self.session.add(AIUsage(tenant_id=self.tenant_id, purpose="dashboard_summary", provider=generation.provider,
            model=generation.model, input_tokens=generation.input_tokens, output_tokens=generation.output_tokens, cost=generation.cost))
        await self.session.commit()
        redis = Redis.from_url(settings.redis_url)
        try:
            await redis.set(cache_key, generation.text, ex=300)
        except Exception:
            pass
        finally:
            await redis.aclose()
        return {"summary": generation.text, "provider": generation.provider}
