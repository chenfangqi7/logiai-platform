from fastapi import FastAPI, HTTPException
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.connectors import router as connectors_router
from app.api.shipments import router as shipments_router
from app.api.exceptions import router as exceptions_router
from app.api.dashboard import router as dashboard_router
from app.api.ai import router as ai_router
from app.api.knowledge import router as knowledge_router
from app.api.webhooks import router as webhooks_router
from app.core.config import get_settings
from app.db.session import engine
from app.demo import router as demo_router

app = FastAPI(title=get_settings().app_name)
app.include_router(auth_router)
app.include_router(connectors_router)
app.include_router(shipments_router)
app.include_router(exceptions_router)
app.include_router(dashboard_router)
app.include_router(ai_router)
app.include_router(knowledge_router)
app.include_router(webhooks_router)
app.include_router(demo_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        redis = Redis.from_url(get_settings().redis_url)
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dependency unavailable") from exc
    return {"status": "ok", "database": "ok", "redis": "ok"}
