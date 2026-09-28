from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.models.domain import FieldMapping
from app.services.mapping import describe_sample_fields, map_shipment, preview_shipment, validate_transform


def mapping(source: str, target: str, transform: dict | None = None, required: bool = False) -> FieldMapping:
    return FieldMapping(tenant_id="tenant", connector_id="connector", entity_type="shipment",
        source_field=source, target_field=target, transform=transform or {}, required=required)


def test_nested_enum_datetime_and_string_transforms():
    mappings = [
        mapping("order.waybillNo", "shipment_no", {"type": "string", "trim": True, "case": "upper", "prefix": "TMS-"}, True),
        mapping("order.status", "status", {"type": "enum", "values": {"30": "IN_TRANSIT"}}),
        mapping("order.depart", "planned_departure_time", {"type": "datetime", "format": "%Y/%m/%d %H:%M:%S", "timezone": "Asia/Shanghai"}),
    ]
    row = {"order": {"waybillNo": " yd-1 ", "status": 30, "depart": "2026/09/28 12:02:15"}}
    converted = map_shipment(row, mappings)
    assert converted.shipment_no == "TMS-YD-1"
    assert converted.status == "IN_TRANSIT"
    assert converted.planned_departure_time.utcoffset() == timedelta(hours=8)
    row["order"]["status"] = 99
    preview = preview_shipment(row, mappings)
    assert preview["transformed"]["status"] == "UNKNOWN"
    assert any(item["level"] == "warning" and item["field"] == "status" for item in preview["validation"])


def test_transform_config_and_canonical_validation():
    with pytest.raises(ValueError, match="standard shipment statuses"):
        validate_transform("status", {"type": "enum", "values": {"99": "INVALID"}})
    with pytest.raises(ValueError, match="unsupported directive"):
        validate_transform("planned_departure_time", {"type": "datetime", "format": "%Q"})
    mappings = [mapping("number", "shipment_no", required=True),
        mapping("depart", "planned_departure_time"), mapping("arrive", "planned_arrival_time")]
    with pytest.raises(ValidationError):
        map_shipment({"number": "X-1", "depart": "2026-09-29", "arrive": "2026-09-28"}, mappings)


def test_sample_field_detection_unions_nested_paths_and_marks_missing_values_nullable():
    fields = describe_sample_fields([{"order": {"waybillNo": "A"}}, {"order": {"waybillNo": "B"}, "driver": {"id": "D-1"}}])
    assert next(item for item in fields if item["path"] == "order.waybillNo")["nullable"] is False
    assert next(item for item in fields if item["path"] == "driver.id")["nullable"] is True
