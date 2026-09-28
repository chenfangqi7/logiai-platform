import logging

from app.ai.gateway.provider import is_llm_configured
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.exception_analysis import ExceptionAnalysisService

logger = logging.getLogger(__name__)


async def analyze_new_exceptions(tenant_id: str, exception_ids: list[str]) -> None:
    if not is_llm_configured():
        return
    for exception_id in exception_ids:
        try:
            async with SessionLocal() as session:
                await ExceptionAnalysisService(session, tenant_id).analyze(exception_id)
        except Exception:
            logger.exception("Exception analysis failed for %s", exception_id)
