from datetime import datetime, timedelta, timezone

import pytest

from app.models.domain import Shipment
from app.rules.evaluator import RuleEvaluator
from app.services.connector import ConnectorService
from test_connector_import import token


def test_rule_evaluator_covers_initial_exception_types():
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    shipment = Shipment(
        tenant_id="tenant", shipment_no="S-1", status="ARRIVED", origin="重庆", destination="秀山",
        planned_departure_time=now - timedelta(hours=8), planned_arrival_time=now - timedelta(hours=3),
        actual_arrival_time=now - timedelta(hours=3), driver_id=None, vehicle_id=None,
    )
    codes = {result.code for result in RuleEvaluator().evaluate(shipment, now)}
    assert codes == {"DEPARTURE_DELAY", "ARRIVAL_DELAY", "UNSIGNED_TOO_LONG", "DATA_MISSING"}
    shipment.status = "IN_TRANSIT"
    shipment.latest_tracking_time = now - timedelta(hours=5)
    codes = {result.code for result in RuleEvaluator().evaluate(shipment, now)}
    assert "TRACKING_STALE" in codes
    shipment.raw_data = {"cold_chain": True}
    levels = {result.code: result.level for result in RuleEvaluator().evaluate(shipment, now)}
    assert levels["TRACKING_STALE"] == "HIGH"
    assert levels["ARRIVAL_DELAY"] == "CRITICAL"


@pytest.mark.asyncio
async def test_import_creates_resolvable_tenant_scoped_exception(client, monkeypatch):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    created = await http.post("/api/v1/connectors", headers=first, json={"name": "TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
        {"source_field": "status", "target_field": "status"},
    ]})

    async def fake_fetch(self, item, sample=False):
        return [{"waybillNo": "YD-EX", "status": "IN_TRANSIT"}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    assert (await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)).json()["imported"] == 1
    response = await http.get("/api/v1/exceptions", headers=first)
    assert response.json()["total"] >= 1
    exception_id = response.json()["items"][0]["id"]
    assert (await http.get(f"/api/v1/exceptions/{exception_id}", headers=second)).status_code == 404
    assert (await http.post(f"/api/v1/exceptions/{exception_id}/resolve", headers=second)).status_code == 404
    resolved = await http.post(f"/api/v1/exceptions/{exception_id}/resolve", headers=first)
    assert resolved.json()["status"] == "resolved"
