import json

import pytest

from test_connector_import import token


@pytest.mark.asyncio
async def test_file_preview_and_import(client):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "File", "type": "file"})
    connector_id = created.json()["id"]
    data = json.dumps([{"waybillNo": "FILE-001", "status": 30}]).encode()
    preview = await http.post(f"/api/v1/connectors/{connector_id}/file-sample", headers=headers, files={"file": ("data.json", data, "application/json")})
    assert preview.status_code == 200, preview.text
    assert "waybillNo" in preview.json()["fields"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers, json={"mappings": [{"source_field": "waybillNo", "target_field": "shipment_no", "required": True}]})
    imported = await http.post(f"/api/v1/connectors/{connector_id}/upload", headers=headers, files={"file": ("data.json", data, "application/json")})
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 1


@pytest.mark.asyncio
async def test_webhook_requires_secret_and_maps_payload(client):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Webhook", "type": "webhook", "config": {"webhook_secret": "private-123"}})
    assert created.status_code == 201, created.text
    assert "webhook_secret" not in created.json()["config"]
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers, json={"mappings": [{"source_field": "waybillNo", "target_field": "shipment_no", "required": True}]})
    denied = await http.post(f"/api/v1/webhooks/{connector_id}", json={"waybillNo": "HOOK-001"}, headers={"X-Webhook-Secret": "wrong"})
    assert denied.status_code == 401
    accepted = await http.post(f"/api/v1/webhooks/{connector_id}", json={"waybillNo": "HOOK-001"}, headers={"X-Webhook-Secret": "private-123"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["imported"] == 1
