import json
from datetime import datetime, timedelta, timezone

import pytest

from app.ai.gateway.llm import Generation
from app.services.connector import ConnectorService
from test_connector_import import token


@pytest.mark.asyncio
async def test_model_exception_analysis_persists_grounded_result(client, monkeypatch):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    created = await http.post("/api/v1/connectors", headers=first, json={
        "name": "Delayed TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments",
    })
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "number", "target_field": "shipment_no", "required": True},
        {"source_field": "state", "target_field": "status"},
        {"source_field": "arrival", "target_field": "planned_arrival_time"},
    ]})

    async def fake_fetch(self, item, sample=False):
        return [{"number": "LATE-001", "state": "IN_TRANSIT",
            "arrival": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    imported = await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    assert imported.status_code == 200, imported.text
    exceptions = await http.get("/api/v1/exceptions", headers=first, params={"type": "ARRIVAL_DELAY"})
    exception_id = exceptions.json()["items"][0]["id"]

    monkeypatch.setattr("app.services.exception_analysis.get_settings", lambda: type("Settings", (), {
        "llm_api_key": "test-key", "llm_model": "test-model",
    })())

    async def fake_generate(self, system, user):
        evidence = json.loads(user)
        assert evidence["shipment"]["shipment_no"] == "LATE-001"
        assert evidence["exception"]["type"] == "ARRIVAL_DELAY"
        return Generation(text=json.dumps({"analysis": "已超过计划到达时间，实际原因尚待核实。",
            "suggestion": "联系司机确认位置并更新预计到达时间。"}, ensure_ascii=False),
            provider="mock-llm", model="test-model", input_tokens=50, output_tokens=30)

    monkeypatch.setattr("app.services.exception_analysis.get_llm_provider", lambda: type("Provider", (), {"generate": fake_generate})())
    analyzed = await http.post(f"/api/v1/exceptions/{exception_id}/analyze", headers=first)
    assert analyzed.status_code == 200, analyzed.text
    assert analyzed.json()["ai_analysis"] == "已超过计划到达时间，实际原因尚待核实。"
    assert analyzed.json()["suggestion"] == "联系司机确认位置并更新预计到达时间。"
    detail = await http.get(f"/api/v1/exceptions/{exception_id}", headers=first)
    assert detail.json()["ai_analysis"] == analyzed.json()["ai_analysis"]
    assert (await http.get(f"/api/v1/exceptions/{exception_id}", headers=second)).status_code == 404
