from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import CollectionMapping, Driver, Route, Shipment, TrackingEvent, Vehicle
from app.repositories.connector import ConnectorRepository
from app.repositories.logistics import LogisticsRepository
from app.schemas.connector import ImportResult
from app.services.common import serialize_model
from app.services.exceptions import ExceptionService
from app.services.mapping import ShipmentImportData, map_shipment, read_field, transform_value
from app.rules.evaluator import aware


def safe_row_error(exc: ValueError | TypeError) -> tuple[str, str]:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        return "CANONICAL_INVALID", f"Invalid {field}: {first['type']}"
    message = str(exc)
    if message.startswith("Missing required field: "):
        return "REQUIRED_MISSING", message
    if message == "Shipment number belongs to another connector":
        return "SOURCE_CONFLICT", message
    if message == "Invalid tracking event time":
        return "TRACKING_TIME_INVALID", message
    return "SOURCE_INVALID", "Invalid source data"


class ShipmentService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.repo = LogisticsRepository(session, tenant_id)

    async def import_rows(self, rows: list[dict], mappings: list, connector_id: str | None = None,
        tracking_mapping: CollectionMapping | None = None, incremental_field: str | None = None) -> ImportResult:
        if not mappings:
            raise ValueError("Configure field mappings before importing")
        imported = updated = rejected = 0
        drivers_created = vehicles_created = routes_created = tracking_events_created = 0
        errors: list[str] = []
        warnings: list[str] = []
        issues: list[dict] = []
        exception_ids: list[str] = []
        checkpoint: str | None = None
        checkpoint_time: datetime | None = None
        for index, row in enumerate(rows):
            try:
                canonical = map_shipment(row, mappings)
                status_source = next((mapping.source_field for mapping in mappings if mapping.target_field == "status"), None)
                if canonical.status == "UNKNOWN" and status_source and read_field(row, status_source) not in (None, "", "UNKNOWN") and len(warnings) < 100:
                    warnings.append(f"Row {index + 1}: unmapped status; using UNKNOWN")
                    issues.append({"row_number": index + 1, "entity": "shipment", "level": "WARNING", "code": "STATUS_UNKNOWN", "message": "Unmapped status; using UNKNOWN"})
                parsed_events = []
                source_events = read_field(row, tracking_mapping.source_field) if tracking_mapping else row.get("trackingEvents", [])
                if source_events is None:
                    source_events = []
                if not isinstance(source_events, list):
                    raise ValueError("Tracking collection must be an array")
                for event in source_events:
                    if not isinstance(event, dict):
                        raise ValueError("Tracking event must be an object")
                    mapped_event = {}
                    if tracking_mapping:
                        for field in tracking_mapping.fields:
                            value = transform_value(read_field(event, field["source_field"]), field.get("transform") or {})
                            if field.get("required") and value in (None, ""):
                                raise ValueError("Tracking event required field missing")
                            if value is not None:
                                mapped_event[field["target_field"]] = value
                    else:
                        mapped_event = event
                    if not mapped_event.get("event_time"):
                        if tracking_mapping:
                            raise ValueError("Tracking event time missing")
                        continue
                    for coordinate, lower, upper in (("longitude", -180, 180), ("latitude", -90, 90)):
                        if mapped_event.get(coordinate) is not None and not lower <= float(mapped_event[coordinate]) <= upper:
                            raise ValueError(f"Invalid {coordinate}")
                    try:
                        event_time = ShipmentImportData.parse_datetime(mapped_event["event_time"])
                        if not isinstance(event_time, datetime):
                            raise ValueError("Invalid tracking event time")
                        parsed_events.append((event, mapped_event, event_time))
                    except ValueError as exc:
                        raise ValueError("Invalid tracking event time") from exc
                row_drivers = row_vehicles = row_routes = row_events = 0
                async with self.session.begin_nested():
                    values = canonical.model_dump(exclude={"driver_external_id", "vehicle_plate_no", "route_name"})
                    source_external_id = canonical.external_id or canonical.shipment_no
                    existing = await self.repo.shipment_by_source(connector_id, source_external_id) if connector_id else None
                    if existing is None:
                        existing = await self.repo.shipment_by_no(canonical.shipment_no)
                    if existing and connector_id and existing.source_connector_id not in (None, connector_id):
                        raise ValueError("Shipment number belongs to another connector")
                    if existing:
                        shipment = existing
                        for key, value in values.items():
                            setattr(shipment, key, value)
                    else:
                        shipment = Shipment(tenant_id=self.tenant_id, **values)
                        self.session.add(shipment)
                    shipment.raw_data = jsonable_encoder(row)
                    if connector_id:
                        shipment.source_connector_id = connector_id
                        shipment.source_external_id = source_external_id
                        source_time = read_field(row, incremental_field) if incremental_field else row.get("updated_at", row.get("updatedAt"))
                        parsed_source_time = ShipmentImportData.parse_datetime(source_time)
                        if isinstance(parsed_source_time, datetime):
                            shipment.source_updated_at = parsed_source_time
                        shipment.last_synced_at = datetime.now(timezone.utc)
                    if canonical.driver_external_id:
                        driver = await self.repo.driver_by_external_id(canonical.driver_external_id)
                        if driver is None:
                            driver = Driver(tenant_id=self.tenant_id, external_id=canonical.driver_external_id, name=str(row.get("driverName") or canonical.driver_external_id), raw_data={})
                            self.session.add(driver)
                            await self.session.flush()
                            row_drivers += 1
                        elif row.get("driverName"):
                            driver.name = str(row["driverName"])
                        shipment.driver_id = driver.id
                    if canonical.vehicle_plate_no:
                        vehicle = await self.repo.vehicle_by_plate(canonical.vehicle_plate_no)
                        if vehicle is None:
                            vehicle = Vehicle(tenant_id=self.tenant_id, plate_no=canonical.vehicle_plate_no, raw_data={})
                            self.session.add(vehicle)
                            await self.session.flush()
                            row_vehicles += 1
                        if row.get("vehicleType"):
                            vehicle.vehicle_type = str(row["vehicleType"])
                        shipment.vehicle_id = vehicle.id
                    if canonical.route_name:
                        route = await self.repo.route_by_name(canonical.route_name)
                        if route is None:
                            route = Route(tenant_id=self.tenant_id, name=canonical.route_name, origin=canonical.origin or "", destination=canonical.destination or "")
                            self.session.add(route)
                            await self.session.flush()
                            row_routes += 1
                        else:
                            route.origin = canonical.origin or route.origin
                            route.destination = canonical.destination or route.destination
                        shipment.route_id = route.id
                    await self.session.flush()
                    known_events = await self.repo.tracking(shipment.id)
                    known_ids = {str(item.external_event_id or item.raw_data.get("external_event_id") or item.raw_data.get("id")) for item in known_events if item.external_event_id or item.raw_data.get("external_event_id") or item.raw_data.get("id")}
                    known_keys = {(item.event_type, aware(item.event_time), item.location) for item in known_events}
                    for event, mapped_event, event_time in parsed_events:
                        event_id = mapped_event.get("external_event_id") or mapped_event.get("id")
                        event_key = (str(mapped_event.get("event_type", "LOCATION")), aware(event_time), mapped_event.get("location"))
                        if (event_id and str(event_id) in known_ids) or event_key in known_keys:
                            continue
                        self.session.add(TrackingEvent(tenant_id=self.tenant_id, shipment_id=shipment.id,
                            event_type=str(mapped_event.get("event_type", "LOCATION")), external_event_id=str(event_id) if event_id else None,
                            location=mapped_event.get("location"), longitude=mapped_event.get("longitude"), latitude=mapped_event.get("latitude"),
                            event_time=event_time, raw_data=jsonable_encoder(event)))
                        if event_id:
                            known_ids.add(str(event_id))
                        known_keys.add(event_key)
                        row_events += 1
                        if shipment.latest_tracking_time is None or aware(event_time) > aware(shipment.latest_tracking_time):
                            shipment.latest_tracking_time = event_time
                    row_exception_ids = await ExceptionService(self.session, self.tenant_id).evaluate_shipment(shipment)
                if existing:
                    updated += 1
                else:
                    imported += 1
                drivers_created += row_drivers
                vehicles_created += row_vehicles
                routes_created += row_routes
                tracking_events_created += row_events
                exception_ids.extend(row_exception_ids)
                if incremental_field:
                    raw_checkpoint = read_field(row, incremental_field)
                    parsed_checkpoint = ShipmentImportData.parse_datetime(raw_checkpoint)
                    if isinstance(parsed_checkpoint, datetime):
                        comparable = aware(parsed_checkpoint)
                        if checkpoint_time is None or comparable > checkpoint_time:
                            checkpoint_time = comparable
                            checkpoint = str(raw_checkpoint)
            except (ValueError, TypeError) as exc:
                rejected += 1
                code, message = safe_row_error(exc)
                issues.append({"row_number": index + 1, "entity": "shipment", "level": "ERROR", "code": code, "message": message})
                if len(errors) < 100:
                    errors.append(f"Row {index + 1}: {message}")
            except SQLAlchemyError as exc:
                rejected += 1
                issues.append({"row_number": index + 1, "entity": "shipment", "level": "ERROR", "code": "DATABASE_ROW_ERROR", "message": "Database rejected this row"})
                if len(errors) < 100:
                    errors.append(f"Row {index + 1}: database error ({type(exc).__name__})")
        await self.session.commit()
        return ImportResult(imported=imported, updated=updated, rejected=rejected, errors=errors, exception_ids=exception_ids,
            total=len(rows), success=imported + updated, failed=rejected, drivers_created=drivers_created,
            vehicles_created=vehicles_created, routes_created=routes_created,
            tracking_events_created=tracking_events_created, warnings=warnings, issues=issues, checkpoint=checkpoint)

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
        source = await ConnectorRepository(self.session, self.tenant_id).get(shipment.source_connector_id) if shipment.source_connector_id else None
        result["source_connector"] = {"id": source.id, "name": source.name} if source else None
        return result
