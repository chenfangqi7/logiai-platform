import pytest

from app.services.connector import ConnectorService


async def token(http, tenant_code: str, password: str) -> dict[str, str]:
    response = await http.post("/api/v1/auth/login", json={"tenant_code": tenant_code, "username": "admin", "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_mapping_import_and_tenant_isolation(client, monkeypatch):
    http, first_id, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    created = await http.post("/api/v1/connectors", headers=first, json={"name": "Mock TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments", "config": {"token": "private-key"}})
    assert created.status_code == 201, created.text
    connector_id = created.json()["id"]
    assert "token" not in created.json()["config"]
    assert (await http.get(f"/api/v1/connectors/{connector_id}", headers=second)).status_code == 404
    mapping = await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
        {"source_field": "status", "target_field": "status", "transform": {"values": {"30": "IN_TRANSIT"}}},
        {"source_field": "fromArea", "target_field": "origin"},
        {"source_field": "toArea", "target_field": "destination"},
    ]})
    assert mapping.status_code == 200, mapping.text
    assert len(mapping.json()) == 4
    assert (await http.get(f"/api/v1/connectors/{connector_id}/mappings", headers=second)).status_code == 404

    async def fake_fetch(self, item, sample=False):
        return [{"waybillNo": "YD-001", "status": 30, "fromArea": "重庆", "toArea": "秀山", "unmapped": "preserved"}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    imported = await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 1
    first_list = await http.get("/api/v1/shipments", headers=first)
    assert first_list.json()["total"] == 1
    shipment = first_list.json()["items"][0]
    assert shipment["tenant_id"] == first_id
    assert shipment["status"] == "IN_TRANSIT"
    assert shipment["raw_data"]["unmapped"] == "preserved"
    assert (await http.get("/api/v1/shipments", headers=second)).json()["total"] == 0
    assert (await http.get(f"/api/v1/shipments/{shipment['id']}", headers=second)).status_code == 404
    again = await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    assert again.json()["updated"] == 1
    assert (await http.get("/api/v1/shipments", headers=first)).json()["total"] == 1
