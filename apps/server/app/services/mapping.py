from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.domain import FieldMapping

STATUSES = {"CREATED", "READY", "PICKED_UP", "IN_TRANSIT", "ARRIVED", "DELIVERING", "DELIVERED", "CANCELLED", "UNKNOWN"}
STATUS_ALIASES = {"10": "CREATED", "20": "READY", "30": "IN_TRANSIT", "40": "DELIVERED", "transporting": "IN_TRANSIT", "delivering": "DELIVERING", "completed": "DELIVERED"}


class CanonicalShipment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shipment_no: str = Field(min_length=1, max_length=100)
    external_id: str | None = None
    status: str = "UNKNOWN"
    origin: str | None = None
    destination: str | None = None
    sender_name: str | None = None
    receiver_name: str | None = None
    planned_departure_time: datetime | None = None
    actual_departure_time: datetime | None = None
    planned_arrival_time: datetime | None = None
    actual_arrival_time: datetime | None = None
    latest_tracking_time: datetime | None = None
    signed_at: datetime | None = None
    driver_external_id: str | None = None
    vehicle_plate_no: str | None = None
    route_name: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> str:
        text = str(value or "UNKNOWN")
        normalized = STATUS_ALIASES.get(text.lower(), text.upper())
        if normalized not in STATUSES:
            raise ValueError(f"Unknown shipment status: {text}")
        return normalized


def read_field(row: dict, path: str) -> Any:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def map_shipment(row: dict, mappings: list[FieldMapping]) -> CanonicalShipment:
    values: dict[str, Any] = {}
    for mapping in mappings:
        value = read_field(row, mapping.source_field)
        if value in (None, ""):
            value = mapping.transform.get("default")
        if mapping.required and value in (None, ""):
            raise ValueError(f"Missing required field: {mapping.source_field}")
        choices = mapping.transform.get("values", {})
        if value is not None and isinstance(choices, dict):
            value = choices.get(str(value), value)
        if value is not None:
            values[mapping.target_field] = value
    return CanonicalShipment.model_validate(values)
