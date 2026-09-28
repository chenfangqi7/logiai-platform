from sqlalchemy.ext.asyncio import AsyncSession

from app.services.common import serialize_model
from app.services.dashboard import DashboardService
from app.services.exceptions import ExceptionService
from app.services.shipments import ShipmentService


class LogisticsTools:
    """Tenant-bound tool facade. AI code never receives a database query interface."""

    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.shipments = ShipmentService(session, tenant_id)
        self.exceptions = ExceptionService(session, tenant_id)
        self.dashboard = DashboardService(session, tenant_id)

    async def search_shipments(self, search: str = "", limit: int = 10, status: str = "") -> dict:
        total, items = await self.shipments.repo.shipments(search=search, status=status, limit=min(limit, 20))
        return {"total": total, "items": [{"id": item.id, "shipment_no": item.shipment_no, "status": item.status,
            "origin": item.origin, "destination": item.destination} for item in items]}

    async def get_shipment(self, shipment_id: str) -> dict | None:
        detail = await self.shipments.detail(shipment_id)
        if detail is None:
            return None
        return {key: detail[key] for key in ("id", "shipment_no", "status", "origin", "destination", "tracking_events", "exceptions")}

    async def get_tracking_events(self, shipment_id: str) -> list[dict]:
        if await self.shipments.repo.shipment(shipment_id) is None:
            return []
        return [serialize_model(item) for item in await self.shipments.repo.tracking(shipment_id)]

    async def get_driver(self, driver_id: str) -> dict | None:
        item = await self.shipments.repo.driver(driver_id)
        if item is None:
            return None
        return {"id": item.id, "name": item.name, "status": item.status}

    async def get_vehicle(self, vehicle_id: str) -> dict | None:
        item = await self.shipments.repo.vehicle(vehicle_id)
        return {"id": item.id, "plate_no": item.plate_no, "status": item.status} if item else None

    async def get_route(self, route_id: str) -> dict | None:
        item = await self.shipments.repo.route(route_id)
        return {"id": item.id, "name": item.name, "origin": item.origin, "destination": item.destination} if item else None

    async def get_exceptions(self, level: str = "", today: bool = False, limit: int = 10) -> dict:
        from app.services.dashboard import china_day_start

        total, items = await self.exceptions.repo.list(
            level=level, levels=("HIGH", "CRITICAL") if level == "HIGH" else None,
            limit=min(limit, 20), since=china_day_start() if today else None,
        )
        return {"total": total, "items": [{"id": item.id, "shipment_id": item.shipment_id, "type": item.type,
            "level": item.level, "status": item.status, "reason": item.reason, "suggestion": item.suggestion} for item in items]}

    async def get_exception_statistics(self, today: bool = True) -> dict:
        return await (self.dashboard.today_exception_stats() if today else self.dashboard.overview())

    async def get_route_exception_statistics(self, route_keyword: str) -> dict | None:
        return await self.dashboard.route_issue_summary(route_keyword)
