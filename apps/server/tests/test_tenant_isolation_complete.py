import pytest

from app.services.connector import ConnectorService
from test_connector_import import token


@pytest.mark.asyncio
async def test_full_cross_tenant_isolation(client, monkeypatch):
    http, first_id, second_id, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")

    # 1. Connectors Isolation
    c_res = await http.post("/api/v1/connectors", headers=first, json={
        "name": "First Tenant TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"
    })
    assert c_res.status_code == 201
    c_id = c_res.json()["id"]

    assert (await http.get(f"/api/v1/connectors/{c_id}", headers=second)).status_code == 404
    assert (await http.put(f"/api/v1/connectors/{c_id}", headers=second, json={"name": "Hacked", "type": "rest"})).status_code == 404
    assert (await http.delete(f"/api/v1/connectors/{c_id}", headers=second)).status_code == 404
    assert (await http.post(f"/api/v1/connectors/{c_id}/test", headers=second)).status_code == 404
    assert (await http.post(f"/api/v1/connectors/{c_id}/sample", headers=second)).status_code == 404
    assert (await http.post(f"/api/v1/connectors/{c_id}/sync", headers=second)).status_code == 404

    # Configure mapping for First tenant
    await http.put(f"/api/v1/connectors/{c_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "no", "target_field": "shipment_no", "required": True},
        {"source_field": "status", "target_field": "status"},
        {"source_field": "origin", "target_field": "origin"},
        {"source_field": "dest", "target_field": "destination"},
    ]})

    # Mock fetch and import 1 shipment for Tenant A
    async def fake_fetch(self, item, sample=False):
        return [{
            "no": "ISOLATION-001",
            "status": "IN_TRANSIT",
            "origin": "Chongqing",
            "dest": "Chengdu",
            "trackingEvents": [{"event_type": "LOCATION", "location": "Chongqing", "event_time": "2026-09-28T08:00:00Z"}]
        }]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    sync_res = await http.post(f"/api/v1/connectors/{c_id}/sync", headers=first)
    assert sync_res.status_code == 200

    # 2. Shipments & Tracking Isolation
    first_shipments = await http.get("/api/v1/shipments", headers=first)
    assert first_shipments.json()["total"] == 1
    s_id = first_shipments.json()["items"][0]["id"]

    second_shipments = await http.get("/api/v1/shipments", headers=second)
    assert second_shipments.json()["total"] == 0

    assert (await http.get(f"/api/v1/shipments/{s_id}", headers=second)).status_code == 404
    assert (await http.get(f"/api/v1/shipments/{s_id}/tracking", headers=second)).status_code == 404
    assert (await http.get(f"/api/v1/shipments/{s_id}/exceptions", headers=second)).status_code == 404

    # 3. Exceptions Isolation
    first_exceptions = await http.get("/api/v1/exceptions", headers=first)
    assert first_exceptions.json()["total"] >= 1
    e_id = first_exceptions.json()["items"][0]["id"]

    second_exceptions = await http.get("/api/v1/exceptions", headers=second)
    assert second_exceptions.json()["total"] == 0

    assert (await http.get(f"/api/v1/exceptions/{e_id}", headers=second)).status_code == 404
    assert (await http.post(f"/api/v1/exceptions/{e_id}/resolve", headers=second)).status_code == 404
    assert (await http.post(f"/api/v1/exceptions/{e_id}/analyze", headers=second)).status_code == 404

    # 4. Dashboard Isolation
    first_dashboard = await http.get("/api/v1/dashboard/overview", headers=first)
    assert first_dashboard.json()["shipments_today"] >= 1

    second_dashboard = await http.get("/api/v1/dashboard/overview", headers=second)
    assert second_dashboard.json()["shipments_today"] == 0
    assert second_dashboard.json()["exception_count"] == 0

    # 5. AI Chat & Conversations Isolation
    chat_res = await http.post("/api/v1/ai/chat", headers=first, json={"message": "今天有多少异常运单？"})
    assert chat_res.status_code == 200
    conv_id = chat_res.json()["conversation_id"]

    assert (await http.get(f"/api/v1/ai/conversations/{conv_id}", headers=second)).status_code == 404
    second_convs = await http.get("/api/v1/ai/conversations", headers=second)
    assert len(second_convs.json()) == 0
