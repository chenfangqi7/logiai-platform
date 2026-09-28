from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Driver, LogisticsException, Route, Shipment, TrackingEvent, Vehicle


class LogisticsRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def shipment_by_no(self, number: str) -> Shipment | None:
        return await self.session.scalar(select(Shipment).where(Shipment.tenant_id == self.tenant_id, Shipment.shipment_no == number))

    async def shipment_by_source(self, connector_id: str, external_id: str) -> Shipment | None:
        return await self.session.scalar(select(Shipment).where(Shipment.tenant_id == self.tenant_id,
            Shipment.source_connector_id == connector_id, Shipment.source_external_id == external_id))

    async def shipment(self, shipment_id: str) -> Shipment | None:
        return await self.session.scalar(select(Shipment).where(Shipment.tenant_id == self.tenant_id, Shipment.id == shipment_id))

    async def shipments(self, search: str = "", status: str = "", offset: int = 0, limit: int = 50) -> tuple[int, list[Shipment]]:
        query = select(Shipment).where(Shipment.tenant_id == self.tenant_id)
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(Shipment.shipment_no.ilike(pattern), Shipment.origin.ilike(pattern), Shipment.destination.ilike(pattern)))
        if status:
            query = query.where(Shipment.status == status)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = list((await self.session.scalars(query.order_by(Shipment.created_at.desc()).offset(offset).limit(limit))).all())
        return total, items

    async def driver_by_external_id(self, external_id: str) -> Driver | None:
        return await self.session.scalar(select(Driver).where(Driver.tenant_id == self.tenant_id, Driver.external_id == external_id))

    async def vehicle_by_plate(self, plate_no: str) -> Vehicle | None:
        return await self.session.scalar(select(Vehicle).where(Vehicle.tenant_id == self.tenant_id, Vehicle.plate_no == plate_no))

    async def route_by_name(self, name: str) -> Route | None:
        return await self.session.scalar(select(Route).where(Route.tenant_id == self.tenant_id, Route.name == name))

    async def driver(self, driver_id: str) -> Driver | None:
        return await self.session.scalar(select(Driver).where(Driver.tenant_id == self.tenant_id, Driver.id == driver_id))

    async def vehicle(self, vehicle_id: str) -> Vehicle | None:
        return await self.session.scalar(select(Vehicle).where(Vehicle.tenant_id == self.tenant_id, Vehicle.id == vehicle_id))

    async def route(self, route_id: str) -> Route | None:
        return await self.session.scalar(select(Route).where(Route.tenant_id == self.tenant_id, Route.id == route_id))

    async def tracking(self, shipment_id: str) -> list[TrackingEvent]:
        return list((await self.session.scalars(select(TrackingEvent).where(TrackingEvent.tenant_id == self.tenant_id, TrackingEvent.shipment_id == shipment_id).order_by(TrackingEvent.event_time))).all())

    async def exceptions_for_shipment(self, shipment_id: str) -> list[LogisticsException]:
        return list((await self.session.scalars(select(LogisticsException).where(LogisticsException.tenant_id == self.tenant_id, LogisticsException.shipment_id == shipment_id).order_by(LogisticsException.detected_at.desc()))).all())
