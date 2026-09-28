from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.ai_usage import AIUsageRepository
from app.services.common import serialize_model


class AIUsageService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = AIUsageRepository(session, tenant_id)

    async def dashboard(self) -> dict:
        tz = ZoneInfo("Asia/Shanghai")
        today_start = datetime.now(timezone.utc).astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        summary = await self.repo.summary(today_start)
        trend = await self.repo.trend(7)
        by_purpose = await self.repo.distribution_by_purpose()
        by_model = await self.repo.distribution_by_model()
        _, recent_items = await self.repo.logs(limit=20, offset=0)

        settings = get_settings()
        models_info = {
            "primary": {
                "provider": settings.llm_provider or "openai-compatible",
                "model": settings.llm_model or "未配置",
                "base_url": settings.llm_base_url or "https://api.openai.com/v1",
                "configured": bool(settings.llm_api_key and settings.llm_model),
            },
            "fallback": {
                "provider": settings.fallback_llm_provider or "qwen",
                "model": settings.fallback_llm_model or "未配置",
                "base_url": settings.fallback_llm_base_url or "",
                "configured": bool(settings.fallback_llm_api_key and settings.fallback_llm_model),
            },
        }

        return {
            "summary": summary,
            "trend": trend,
            "distribution_by_purpose": by_purpose,
            "distribution_by_model": by_model,
            "models_info": models_info,
            "recent_logs": [serialize_model(item) for item in recent_items],
        }

    async def logs(self, offset: int = 0, limit: int = 50) -> dict:
        total, items = await self.repo.logs(limit=limit, offset=offset)
        return {"total": total, "items": [serialize_model(item) for item in items]}
