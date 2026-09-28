import pytest
from datetime import datetime, timedelta, timezone

from app.services.connector import ConnectorService
from test_connector_import import token


@pytest.mark.asyncio
async def test_ai_answer_is_grounded_and_conversation_is_tenant_scoped(client, monkeypatch):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    connector = await http.post("/api/v1/connectors", headers=first, json={"name": "TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = connector.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
        {"source_field": "status", "target_field": "status"},
    ]})

    async def fake_fetch(self, item, sample=False):
        return [{"waybillNo": "YD202609280001", "status": 30}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    answer = await http.post("/api/v1/ai/chat", headers=first, json={"message": "今天有多少异常运单？"})
    assert answer.status_code == 200, answer.text
    assert "1 票异常运单" in answer.json()["answer"]
    conversation_id = answer.json()["conversation_id"]
    assert (await http.get(f"/api/v1/ai/conversations/{conversation_id}", headers=second)).status_code == 404
    detail = await http.get(f"/api/v1/ai/conversations/{conversation_id}", headers=first)
    assert len(detail.json()["messages"]) == 2
    assert detail.json()["messages"][1]["provider"] == "rules"
    shipment_answer = await http.post("/api/v1/ai/chat", headers=first, json={"message": "运单YD202609280001发生了什么？"})
    assert "YD202609280001" in shipment_answer.json()["answer"]
    in_transit_answer = await http.post("/api/v1/ai/chat", headers=first, json={"message": "当前在途运单情况怎么样？"})
    assert "在途运单" in in_transit_answer.json()["answer"]


@pytest.mark.asyncio
async def test_knowledge_search_enforces_tenant_scope(client):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    created = await http.post("/api/v1/knowledge/text", headers=first, json={"title": "异常处理 SOP", "content": "运输延误异常处理：先联系司机核实位置，再通知客户预计到达时间。"})
    assert created.status_code == 201, created.text
    document_id = created.json()["id"]
    assert (await http.get("/api/v1/knowledge/search?q=运输延误异常处理", headers=first)).json()
    assert (await http.get("/api/v1/knowledge/search?q=运输延误异常处理", headers=second)).json() == []
    assert (await http.get(f"/api/v1/knowledge/{document_id}", headers=second)).status_code == 404
    answer = await http.post("/api/v1/ai/chat", headers=first, json={"message": "运输延误异常如何处理？"})
    assert "参考知识库" in answer.json()["answer"]
    other_answer = await http.post("/api/v1/ai/chat", headers=second, json={"message": "运输延误异常如何处理？"})
    assert "参考知识库" not in other_answer.json()["answer"]


@pytest.mark.asyncio
async def test_priority_answer_includes_critical_exceptions(client, monkeypatch):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=first, json={
        "name": "Cold Chain", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments",
    })
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "number", "target_field": "shipment_no", "required": True},
        {"source_field": "state", "target_field": "status"},
        {"source_field": "arrival", "target_field": "planned_arrival_time"},
    ]})

    async def fake_fetch(self, item, sample=False):
        return [{"number": "COLD-001", "state": "IN_TRANSIT", "cold_chain": True,
            "arrival": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    imported = await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    assert imported.status_code == 200, imported.text
    answer = await http.post("/api/v1/ai/chat", headers=first, json={"message": "哪些高风险异常需要优先处理？"})
    assert answer.status_code == 200, answer.text
    assert answer.json()["grounding"]["total"] == 1
    assert answer.json()["grounding"]["items"][0]["level"] == "CRITICAL"
