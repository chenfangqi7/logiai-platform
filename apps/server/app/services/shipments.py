from datetime import datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Driver, Route, Shipment, TrackingEvent, Vehicle
from app.repositories.logistics import LogisticsRepository
from app.schemas.connector import ImportResult
from app.services.common import serialize_model
from app.services.exceptions import ExceptionService
from app.services.mapping import map_shipment
from app.rules.evaluator import aware


class ShipmentService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = LogisticsRepository(session, tenant_id)

    async def import_rows(self, rows: list[dict], mappings: list) -> ImportResult:
        if not mappings:
            raise ValueError("Configure field mappings before importing")
        imported = updated = rejected = 0
        errors: list[str] = []
        exception_ids: list[str] = []
        for index, row in enumerate(rows):
            try:
                canonical = map_shipment(row, mappings)
                parsed_events = []
                for event in row.get("trackingEvents", []):
                    if not isinstance(event, dict) or not event.get("event_time"):
                        continue
                    parsed_events.append((event, datetime.fromisoformat(str(event["event_time"]).replace("Z", "+00:00"))))
                values = canonical.model_dump(exclude={"driver_external_id", "vehicle_plate_no", "route_name"})
                existing = await self.repo.shipment_by_no(canonical.shipment_no)
                if existing:
                    shipment = existing
                    for key, value in values.items():
                        setattr(shipment, key, value)
                    updated += 1
                else:
                    shipment = Shipment(tenant_id=self.tenant_id, **values)
                    self.session.add(shipment)
                    imported += 1
                shipment.raw_data = jsonable_encoder(row)
                if canonical.driver_external_id:
                    driver = await self.repo.driver_by_external_id(canonical.driver_external_id)
                    if driver is None:
                        driver = Driver(tenant_id=self.tenant_id, external_id=canonical.driver_external_id, name=canonical.driver_external_id, raw_data={})
                        self.session.add(driver)
                        await self.session.flush()
                    shipment.driver_id = driver.id
                if canonical.vehicle_plate_no:
                    vehicle = await self.repo.vehicle_by_plate(canonical.vehicle_plate_no)
                    if vehicle is None:
                        vehicle = Vehicle(tenant_id=self.tenant_id, plate_no=canonical.vehicle_plate_no, raw_data={})
                        self.session.add(vehicle)
                        await self.session.flush()
                    shipment.vehicle_id = vehicle.id
                if canonical.route_name:
                    route = await self.repo.route_by_name(canonical.route_name)
                    if route is None:
                        route = Route(tenant_id=self.tenant_id, name=canonical.route_name, origin=canonical.origin or "", destination=canonical.destination or "")
                        self.session.add(route)
                        await self.session.flush()
                    shipment.route_id = route.id
                await self.session.flush()
                if existing is None:
                    for event, event_time in parsed_events:
                        self.session.add(TrackingEvent(tenant_id=self.tenant_id, shipment_id=shipment.id,
                            event_type=str(event.get("event_type", "LOCATION")), location=event.get("location"),
                            longitude=event.get("longitude"), latitude=event.get("latitude"),
                            event_time=event_time, raw_data=jsonable_encoder(event)))
                        if shipment.latest_tracking_time is None or aware(event_time) > aware(shipment.latest_tracking_time):
                            shipment.latest_tracking_time = event_time
                exception_ids.extend(await ExceptionService(self.session, self.tenant_id).evaluate_shipment(shipment))
            except (ValueError, TypeError) as exc:
                rejected += 1
                if len(errors) < 10:
                    errors.append(f"Row {index + 1}: {exc}")
        await self.session.commit()
        return ImportResult(imported=imported, updated=updated, rejected=rejected, errors=errors, exception_ids=exception_ids)

    async def detail(self, shipment_id: str) -> dict | None:
        shipment = await self.repo.shipment(shipment_id)
        if shipment is None:
            return None
        result = serialize_model(shipment)
        result["tracking_events"] = [serialize_model(item) for item in await self.repo.tracking(shipment_id)]
        result["exceptions"] = [serialize_model(item) for item in await self.repo.exceptions_for_shipment(shipment_id)]
        result["driver"] = serialize_model(await self.repo.driver(shipment.driver_id)) if shipment.driver_id else None
        if result["driver"]:
            result["driver"].pop("phone", None)
        result["vehicle"] = serialize_model(await self.repo.vehicle(shipment.vehicle_id)) if shipment.vehicle_id else None
        result["route"] = serialize_model(await self.repo.route(shipment.route_id)) if shipment.route_id else None
        return result
