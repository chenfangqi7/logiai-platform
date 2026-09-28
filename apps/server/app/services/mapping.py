from datetime import datetime, timezone
from difflib import SequenceMatcher
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.models.domain import FieldMapping

STATUSES = {"CREATED", "READY", "PICKED_UP", "IN_TRANSIT", "ARRIVED", "DELIVERING", "DELIVERED", "CANCELLED", "UNKNOWN"}
STATUS_ALIASES = {"10": "CREATED", "20": "READY", "30": "IN_TRANSIT", "40": "DELIVERED", "transporting": "IN_TRANSIT", "delivering": "DELIVERING", "completed": "DELIVERED"}


class ShipmentImportData(BaseModel):
    """Validated data between external records and the import service."""
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
        return normalized if normalized in STATUSES else "UNKNOWN"

    @field_validator("planned_departure_time", "actual_departure_time", "planned_arrival_time", "actual_arrival_time", "latest_tracking_time", "signed_at", mode="before")
    @classmethod
    def parse_datetime(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            ts = value / 1000.0 if value > 1e11 else float(value)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(value, str):
            if len(value.strip()) == 14 and value.strip().isdigit():
                return datetime.strptime(value.strip(), "%Y%m%d%H%M%S")
            text = value.strip().replace("Z", "+00:00").replace("/", "-")
            if " " in text and "T" not in text:
                text = text.replace(" ", "T")
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                pass
        return value

    @model_validator(mode="after")
    def validate_time_order(self) -> "ShipmentImportData":
        if self.planned_departure_time and self.planned_arrival_time:
            departure = self.planned_departure_time
            arrival = self.planned_arrival_time
            if departure.tzinfo is None:
                departure = departure.replace(tzinfo=timezone.utc)
            if arrival.tzinfo is None:
                arrival = arrival.replace(tzinfo=timezone.utc)
            if arrival < departure:
                raise ValueError("planned_arrival_time must be after planned_departure_time")
        return self


# Keep the original name for existing import callers.
CanonicalShipment = ShipmentImportData

DATETIME_FIELDS = {"planned_departure_time", "actual_departure_time", "planned_arrival_time", "actual_arrival_time", "latest_tracking_time", "signed_at", "event_time"}
TRANSFORM_TYPES = {"none", "enum", "datetime", "number", "boolean", "string", "default", "fixed", "constant"}
FIELD_ALIASES = {
    "shipment_no": {"waybillno", "waybillcode", "waybill_no", "orderno", "order_id", "shipmentno", "shipment_no"},
    "status": {"status", "state", "orderstatus"},
    "origin": {"origin", "fromarea", "startcity"},
    "destination": {"destination", "toarea", "endcity"},
    "sender_name": {"sender", "sendname", "consignor", "consignorname"},
    "receiver_name": {"receiver", "receivename", "consignee", "consigneename"},
    "driver_external_id": {"drivercode", "driverid", "driver.id"},
    "vehicle_plate_no": {"plateno", "vehicleplateno", "vehicle.plateno"},
    "route_name": {"routename", "route.name"},
    "planned_departure_time": {"plandepart", "planneddeparturetime"},
    "actual_departure_time": {"actualdepart", "actualdeparturetime"},
    "planned_arrival_time": {"planarrive", "plannedarrivaltime"},
    "actual_arrival_time": {"actualarrive", "actualarrivaltime"},
}


def describe_fields(row: dict, prefix: str = "", depth: int = 0) -> list[dict]:
    fields: list[dict] = []
    if depth > 5:
        return fields
    for key, value in row.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            fields.extend(describe_fields(value, path, depth + 1))
        else:
            field_type = "array" if isinstance(value, list) else "null" if value is None else "boolean" if isinstance(value, bool) else "number" if isinstance(value, (int, float)) else "string"
            fields.append({"path": path, "type": field_type, "nullable": value is None,
                           "sample_value": value[:2] if isinstance(value, list) else value})
        if len(fields) >= 200:
            break
    return fields[:200]


def describe_sample_fields(rows: list[dict]) -> list[dict]:
    collected: dict[str, dict] = {}
    for index, row in enumerate(rows[:5]):
        present: set[str] = set()
        for field in describe_fields(row):
            path = field["path"]
            present.add(path)
            if path not in collected:
                collected[path] = {**field, "nullable": index > 0 or field["nullable"]}
            elif field["sample_value"] is not None and collected[path]["sample_value"] is None:
                collected[path]["sample_value"] = field["sample_value"]
                collected[path]["type"] = field["type"]
            if field["nullable"]:
                collected[path]["nullable"] = True
        for path in collected.keys() - present:
            collected[path]["nullable"] = True
    return list(collected.values())[:200]


def suggest_mappings(source_fields: list[str]) -> list[dict]:
    suggestions: list[dict] = []
    used: set[str] = set()
    for source in source_fields:
        leaf = source.split(".")[-1]
        normalized = re.sub(r"[^a-z0-9]", "", leaf.lower())
        normalized_full = re.sub(r"[^a-z0-9]", "", source.lower())
        ranked: list[tuple[float, str]] = []
        for target, aliases in FIELD_ALIASES.items():
            names = {target, *aliases}
            score = max(max(SequenceMatcher(None, candidate, re.sub(r"[^a-z0-9]", "", name.lower())).ratio()
                            for candidate in {normalized, normalized_full}) for name in names)
            ranked.append((score, target))
        score, target = max(ranked)
        if score >= 0.78 and target not in used:
            suggestions.append({"source_field": source, "target_field": target, "confidence": round(score, 2)})
            used.add(target)
    return suggestions


def validate_transform(target_field: str, config: dict) -> None:
    kind = config.get("type", "enum" if "values" in config else "none")
    if kind not in TRANSFORM_TYPES:
        raise ValueError(f"Unsupported transform type: {kind}")
    if kind == "enum":
        choices = config.get("values")
        if not isinstance(choices, dict) or not choices:
            raise ValueError("Enum transform requires nonempty values")
        if target_field == "status" and any(str(value).upper() not in STATUSES for value in choices.values()):
            raise ValueError("Enum status values must be standard shipment statuses")
    if kind == "datetime":
        if target_field not in DATETIME_FIELDS:
            raise ValueError("Datetime transform requires a datetime target field")
        if config.get("format") is not None and (not isinstance(config["format"], str) or not config["format"].strip()):
            raise ValueError("Datetime format must be a nonempty string")
        if config.get("format") and any(code not in "aAbBcdHIjmMpSUwWxXyYZfzGUVu%" for code in re.findall(r"%(.)", config["format"])):
            raise ValueError("Datetime format contains an unsupported directive")
        if config.get("timezone"):
            try:
                ZoneInfo(config["timezone"])
            except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
                raise ValueError("Invalid datetime timezone") from exc
    if kind in {"default", "fixed", "constant"} and "value" not in config:
        raise ValueError(f"{kind} transform requires value")
    if kind == "string" and config.get("case") not in (None, "upper", "lower"):
        raise ValueError("String case must be upper or lower")
    if kind == "string" and config.get("replace") is not None:
        replace = config["replace"]
        if not isinstance(replace, dict) or not isinstance(replace.get("from"), str) or not replace["from"]:
            raise ValueError("String replace requires a nonempty from value")


def read_field(row: dict, path: str) -> Any:
    value: Any = row
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def transform_value(value: Any, config: dict) -> Any:
    kind = config.get("type", "enum" if "values" in config else "none")
    if kind in {"fixed", "constant"}:
        return config["value"]
    if value in (None, ""):
        value = config.get("value") if kind == "default" else config.get("default")
    if value in (None, ""):
        return value
    if kind == "enum":
        return config["values"].get(str(value), value)
    if kind == "datetime":
        parsed = datetime.strptime(str(value), config["format"]) if config.get("format") else ShipmentImportData.parse_datetime(value)
        if not isinstance(parsed, datetime):
            raise ValueError(f"Invalid datetime: {value}")
        if config.get("timezone") and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(config["timezone"]))
        return parsed
    if kind == "number":
        return float(value)
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
        raise ValueError(f"Invalid boolean: {value}")
    if kind == "string":
        result = str(value)
        if config.get("trim"):
            result = result.strip()
        if config.get("case") == "upper":
            result = result.upper()
        elif config.get("case") == "lower":
            result = result.lower()
        if config.get("replace"):
            result = result.replace(config["replace"]["from"], str(config["replace"].get("to", "")))
        result = f"{config.get('prefix', '')}{result}{config.get('suffix', '')}"
        return result
    return value


def map_shipment(row: dict, mappings: list[FieldMapping]) -> CanonicalShipment:
    values: dict[str, Any] = {}
    for mapping in mappings:
        value = transform_value(read_field(row, mapping.source_field), mapping.transform or {})
        if (mapping.required or mapping.target_field == "shipment_no") and value in (None, ""):
            raise ValueError(f"Missing required field: {mapping.source_field}")
        if value is not None:
            values[mapping.target_field] = value
    return ShipmentImportData.model_validate(values)


def preview_shipment(row: dict, mappings: list[FieldMapping]) -> dict:
    validation: list[dict[str, str]] = []
    values: dict[str, Any] = {}
    for mapping in mappings:
        field = mapping.target_field
        try:
            value = transform_value(read_field(row, mapping.source_field), mapping.transform or {})
            if value in (None, ""):
                level = "error" if mapping.required or field == "shipment_no" else "warning"
                validation.append({"field": field, "level": level, "message": "required value missing" if level == "error" else "value is empty"})
            else:
                values[field] = value
                if field == "status" and ShipmentImportData.normalize_status(value) == "UNKNOWN" and str(value).upper() != "UNKNOWN":
                    validation.append({"field": field, "level": "warning", "message": f"unmapped status: {value}; using UNKNOWN"})
                else:
                    validation.append({"field": field, "level": "success", "message": "valid"})
        except (ValueError, TypeError, KeyError) as exc:
            validation.append({"field": field, "level": "error", "message": str(exc)})
    try:
        transformed = ShipmentImportData.model_validate(values).model_dump(mode="json", exclude_none=True)
    except ValidationError as exc:
        transformed = values
        for error in exc.errors():
            validation.append({"field": str(error["loc"][0]), "level": "error", "message": error["msg"]})
    return {"source": row, "transformed": transformed, "validation": validation}
