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
    assert len((await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs", headers=first)).json()) == 2


@pytest.mark.asyncio
async def test_mapping_import_with_various_time_formats(client, monkeypatch):
    http, first_id, _, _ = client
    first = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=first, json={"name": "Time Format TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [
        {"source_field": "order_id", "target_field": "shipment_no", "required": True},
        {"source_field": "depart_str", "target_field": "planned_departure_time"},
        {"source_field": "arrive_ts", "target_field": "planned_arrival_time"},
    ]})

    async def fake_fetch(self, item, sample=False):
        return [
            {"order_id": "TIME-001", "depart_str": "2026/09/28 08:30:00", "arrive_ts": 1790589600},
            {"order_id": "TIME-002", "depart_str": "2026-09-28 10:00:00", "arrive_ts": 1790589600000},
        ]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    imported = await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 2
    res = await http.get("/api/v1/shipments", headers=first, params={"search": "TIME-"})
    assert res.json()["total"] == 2
    items = res.json()["items"]
    assert all(item["planned_departure_time"] is not None for item in items)
    assert all(item["planned_arrival_time"] is not None for item in items)


@pytest.mark.asyncio
async def test_mapping_preview_validates_without_importing(client):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    created = await http.post("/api/v1/connectors", headers=first, json={"name": "Preview", "type": "file"})
    connector_id = created.json()["id"]
    payload = {"sample": {"waybillNo": "PREVIEW-001", "status": 99, "depart": "20260928120215"}, "mappings": [
        {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
        {"source_field": "status", "target_field": "status"},
        {"source_field": "depart", "target_field": "planned_departure_time", "transform": {"type": "datetime", "timezone": "Asia/Shanghai"}},
    ]}
    assert (await http.post(f"/api/v1/connectors/{connector_id}/mapping/preview", headers=second, json=payload)).status_code == 404
    response = await http.post(f"/api/v1/connectors/{connector_id}/mapping/preview", headers=first, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["transformed"]["status"] == "UNKNOWN"
    assert response.json()["transformed"]["planned_departure_time"].startswith("2026-09-28T12:02:15")
    assert any(item["field"] == "status" and item["level"] == "warning" for item in response.json()["validation"])
    assert (await http.get("/api/v1/shipments", headers=first)).json()["total"] == 0
    fields = await http.get("/api/v1/mapping/fields/shipment", headers=first)
    assert fields.status_code == 200
    assert next(item for item in fields.json() if item["name"] == "shipment_no")["required"] is True
    invalid = payload | {"mappings": [payload["mappings"][0], {"source_field": "status", "target_field": "status", "transform": {"type": "enum", "values": {"99": "INVALID"}}}]}
    assert (await http.post(f"/api/v1/connectors/{connector_id}/mapping/preview", headers=first, json=invalid)).status_code == 422


@pytest.mark.asyncio
async def test_import_keeps_valid_rows_and_deduplicates_new_tracking_events(client):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Tracking", "type": "file"})
    connector_id = created.json()["id"]
    mappings = [
        {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
        {"source_field": "driverCode", "target_field": "driver_external_id"},
        {"source_field": "plateNo", "target_field": "vehicle_plate_no"},
        {"source_field": "routeName", "target_field": "route_name"},
    ]
    assert (await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers, json={"mappings": mappings})).status_code == 200
    row = {"waybillNo": "TRACK-001", "driverCode": "D-1", "plateNo": "渝A12345", "routeName": "重庆-秀山",
           "trackingEvents": [{"id": "E-1", "event_time": "2026-09-28T08:00:00Z", "location": "重庆"}]}
    first = await http.post(f"/api/v1/connectors/{connector_id}/import", headers=headers, json=[{"waybillNo": ""}, row])
    assert first.status_code == 200, first.text
    assert first.json()["total"] == 2 and first.json()["success"] == 1 and first.json()["failed"] == 1
    assert first.json()["tracking_events_created"] == 1
    assert first.json()["drivers_created"] == 1 and first.json()["vehicles_created"] == 1
    second = await http.post(f"/api/v1/connectors/{connector_id}/import", headers=headers, json=[row | {"trackingEvents": row["trackingEvents"] + [{"id": "E-2", "event_time": "2026-09-28T09:00:00Z", "location": "秀山"}]}])
    assert second.status_code == 200, second.text
    assert second.json()["updated"] == 1 and second.json()["tracking_events_created"] == 1
    shipment = (await http.get("/api/v1/shipments", headers=headers)).json()["items"][0]
    detail = (await http.get(f"/api/v1/shipments/{shipment['id']}", headers=headers)).json()
    assert len(detail["tracking_events"]) == 2


@pytest.mark.asyncio
async def test_source_identity_survives_shipment_number_change(client):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Source TMS", "type": "file"})
    connector_id = created.json()["id"]
    mappings = [
        {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
        {"source_field": "id", "target_field": "external_id"},
    ]
    assert (await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers, json={"mappings": mappings})).status_code == 200
    first = await http.post(f"/api/v1/connectors/{connector_id}/import", headers=headers,
        json=[{"id": "EXT-001", "waybillNo": "OLD-NO", "updated_at": "2026-09-28T10:00:00Z"}])
    assert first.json()["imported"] == 1
    second = await http.post(f"/api/v1/connectors/{connector_id}/import", headers=headers,
        json=[{"id": "EXT-001", "waybillNo": "NEW-NO", "updated_at": "2026-09-28T11:00:00Z"}])
    assert second.json()["updated"] == 1, second.text
    shipments = (await http.get("/api/v1/shipments", headers=headers)).json()
    assert shipments["total"] == 1
    detail = (await http.get(f"/api/v1/shipments/{shipments['items'][0]['id']}", headers=headers)).json()
    assert detail["shipment_no"] == "NEW-NO"
    assert detail["source_connector"]["name"] == "Source TMS"
    assert detail["source_external_id"] == "EXT-001"
    assert detail["source_updated_at"] is not None and detail["last_synced_at"] is not None


@pytest.mark.asyncio
async def test_sync_job_history_and_tenant_scope(client, monkeypatch):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    created = await http.post("/api/v1/connectors", headers=first, json={"name": "Job TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first,
        json={"mappings": [{"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
                           {"source_field": "depart", "target_field": "planned_departure_time"}]})

    async def fake_fetch(self, item, sample=False):
        return [{"waybillNo": "JOB-001"}, {"waybillNo": "JOB-002", "depart": "Bearer private-key"}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    started = await http.post(f"/api/v1/connectors/{connector_id}/sync-jobs", headers=first)
    assert started.status_code == 202, started.text
    job_id = started.json()["id"]
    assert (await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{job_id}", headers=second)).status_code == 404
    result = await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{job_id}", headers=first)
    assert result.status_code == 200
    assert result.json()["status"] == "PARTIAL_SUCCESS", result.text
    assert result.json()["success_count"] == 1 and result.json()["failed_count"] == 1
    assert result.json()["result"]["errors"]
    issues = await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{job_id}/issues", headers=first)
    assert issues.status_code == 200 and issues.json()[0]["level"] == "ERROR"
    assert "private-key" not in issues.text and "private-key" not in result.text
    assert (await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{job_id}/issues", headers=second)).status_code == 404
    history = await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs", headers=first)
    assert len(history.json()) == 1


@pytest.mark.asyncio
async def test_nested_sample_fields_and_mapping_suggestions(client, monkeypatch):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Nested", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = created.json()["id"]

    async def fake_fetch(self, item, sample=False):
        return [{"order": {"waybillNo": "NEST-001"}, "driver": {"id": "D-1"}, "trackingEvents": [{"event_time": "2026-09-28T08:00:00Z"}]}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    sample = await http.post(f"/api/v1/connectors/{connector_id}/sample", headers=headers)
    assert sample.status_code == 200
    assert "order.waybillNo" in sample.json()["fields"]
    assert next(item for item in sample.json()["field_details"] if item["path"] == "trackingEvents")["type"] == "array"
    suggested = await http.post("/api/v1/mapping/suggestions", headers=headers, json=sample.json()["fields"])
    assert {item["source_field"]: item["target_field"] for item in suggested.json()}["order.waybillNo"] == "shipment_no"
    assert {item["source_field"]: item["target_field"] for item in suggested.json()}["driver.id"] == "driver_external_id"


@pytest.mark.asyncio
async def test_nested_tracking_collection_mapping_and_deduplication(client):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Nested tracking", "type": "file"})
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers,
        json={"mappings": [{"source_field": "order.number", "target_field": "shipment_no", "required": True}]})
    tracking = {"source_field": "journey.events", "fields": [
        {"source_field": "event.id", "target_field": "external_event_id"},
        {"source_field": "event.kind", "target_field": "event_type"},
        {"source_field": "place", "target_field": "location"},
        {"source_field": "at", "target_field": "event_time", "required": True},
    ]}
    saved = await http.put(f"/api/v1/connectors/{connector_id}/tracking-mapping", headers=headers, json=tracking)
    assert saved.status_code == 200, saved.text
    assert (await http.get(f"/api/v1/connectors/{connector_id}/tracking-mapping", headers=headers)).json()["source_field"] == "journey.events"
    row = {"order": {"number": "NEST-TRACK-001"}, "journey": {"events": [
        {"event": {"id": "EVT-1", "kind": "LOCATION"}, "place": "重庆", "at": "2026-09-28T08:00:00Z"}]}}
    first = await http.post(f"/api/v1/connectors/{connector_id}/import", headers=headers, json=[row])
    assert first.json()["tracking_events_created"] == 1, first.text
    changed_time = {**row, "journey": {"events": [{"event": {"id": "EVT-1", "kind": "LOCATION"}, "place": "重庆", "at": "2026-09-28T09:00:00Z"}]}}
    second = await http.post(f"/api/v1/connectors/{connector_id}/import", headers=headers, json=[changed_time])
    assert second.json()["tracking_events_created"] == 0, second.text
    shipment = (await http.get("/api/v1/shipments", headers=headers)).json()["items"][0]
    detail = (await http.get(f"/api/v1/shipments/{shipment['id']}", headers=headers)).json()
    assert len(detail["tracking_events"]) == 1
    assert detail["tracking_events"][0]["external_event_id"] == "EVT-1"


@pytest.mark.asyncio
async def test_incremental_checkpoint_uses_latest_successful_source_record(client, monkeypatch):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Incremental", "type": "rest",
        "base_url": "http://localhost:8000/demo/tms/shipments",
        "config": {"sync_mode": "INCREMENTAL", "incremental_field": "meta.updatedAt", "incremental_param": "since"}})
    assert created.status_code == 201, created.text
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers,
        json={"mappings": [{"source_field": "waybillNo", "target_field": "shipment_no", "required": True}]})

    async def fake_fetch(self, item, sample=False):
        return [{"waybillNo": "INC-1", "meta": {"updatedAt": "2026-09-28T08:00:00Z"}},
                {"waybillNo": "INC-2", "meta": {"updatedAt": "2026-09-28T09:00:00Z"}},
                {"waybillNo": "", "meta": {"updatedAt": "2026-09-28T10:00:00Z"}}]

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    synced = await http.post(f"/api/v1/connectors/{connector_id}/sync-jobs", headers=headers)
    assert synced.status_code == 202
    job = await http.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{synced.json()['id']}", headers=headers)
    assert job.json()["result"]["checkpoint"] == "2026-09-28T09:00:00Z"
    connector = await http.get(f"/api/v1/connectors/{connector_id}", headers=headers)
    assert connector.json()["config"]["last_sync_value"] == "2026-09-28T09:00:00Z"


@pytest.mark.asyncio
async def test_same_connector_rejects_concurrent_sync_jobs(client, monkeypatch):
    http, _, _, _ = client
    headers = await token(http, "first", "correct-password")
    created = await http.post("/api/v1/connectors", headers=headers, json={"name": "Concurrent", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = created.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=headers,
        json={"mappings": [{"source_field": "waybillNo", "target_field": "shipment_no", "required": True}]})

    async def keep_pending(*args):
        return None

    monkeypatch.setattr("app.api.connectors.run_sync_job", keep_pending)
    first = await http.post(f"/api/v1/connectors/{connector_id}/sync-jobs", headers=headers)
    assert first.status_code == 202
    second = await http.post(f"/api/v1/connectors/{connector_id}/sync-jobs", headers=headers)
    assert second.status_code == 409
