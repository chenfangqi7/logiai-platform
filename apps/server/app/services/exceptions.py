from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import LogisticsException, Shipment
from app.repositories.exceptions import ExceptionRepository
from app.rules.evaluator import RuleEvaluator


class ExceptionService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = ExceptionRepository(session, tenant_id)
        self.evaluator = RuleEvaluator()

    async def evaluate_shipment(self, shipment: Shipment, now: datetime | None = None) -> list[str]:
        if shipment.tenant_id != self.tenant_id:
            raise ValueError("Shipment is outside tenant scope")
        now = now or datetime.now(timezone.utc)
        created: list[LogisticsException] = []
        for result in self.evaluator.evaluate(shipment, now):
            existing = await self.repo.by_rule(shipment.id, result.code)
            if existing is None:
                item = LogisticsException(
                    tenant_id=self.tenant_id, shipment_id=shipment.id, type=result.code, level=result.level,
                    status="open", rule_code=result.code, reason=result.reason, suggestion=result.suggestion,
                    ai_analysis=f"规则分析：{result.reason}", detected_at=now,
                )
                self.session.add(item)
                created.append(item)
        await self.session.flush()
        return [item.id for item in created]

    async def resolve(self, item: LogisticsException) -> LogisticsException:
        if item.tenant_id != self.tenant_id:
            raise ValueError("Exception is outside tenant scope")
        item.status = "resolved"
        item.resolved_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(item)
        return item
