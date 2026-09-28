"""Exercise the Connector -> Mapping -> Sync -> Shipment acceptance flow against a running server."""

import asyncio
from datetime import datetime, timezone
import os

import httpx


async def main() -> None:
    prefix = "T" + datetime.now(timezone.utc).strftime("%m%d%H%M%S")
    base = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001")
    source_url = f"http://server:8000/demo/tms/shipments?prefix={prefix}"
    async with httpx.AsyncClient(base_url=base, timeout=90) as client:
        login = await client.post("/api/v1/auth/login", json={"tenant_code": "demo", "username": "admin", "password": os.getenv("DEV_ADMIN_PASSWORD", "123456")})
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        created = await client.post("/api/v1/connectors", json={"name": f"验收 TMS {prefix}", "type": "rest", "base_url": source_url})
        created.raise_for_status()
        connector_id = created.json()["id"]
        connection = await client.post(f"/api/v1/connectors/{connector_id}/test")
        connection.raise_for_status()
        assert connection.json()["status_code"] == 200
        sample = await client.post(f"/api/v1/connectors/{connector_id}/sample")
        sample.raise_for_status()
        assert any(item["path"] == "status" and item["type"] == "number" for item in sample.json()["field_details"])
        suggestions = await client.post("/api/v1/mapping/suggestions", json=sample.json()["fields"])
        suggestions.raise_for_status()
        assert any(item["target_field"] == "shipment_no" for item in suggestions.json())
        mappings = [
            {"source_field": "waybillNo", "target_field": "shipment_no", "required": True},
            {"source_field": "status", "target_field": "status", "transform": {"type": "enum", "values": {"30": "IN_TRANSIT", "40": "DELIVERED"}}},
            {"source_field": "fromArea", "target_field": "origin"},
            {"source_field": "toArea", "target_field": "destination"},
            {"source_field": "planDepart", "target_field": "planned_departure_time"},
            {"source_field": "planArrive", "target_field": "planned_arrival_time"},
            {"source_field": "driverCode", "target_field": "driver_external_id"},
            {"source_field": "plateNo", "target_field": "vehicle_plate_no"},
            {"source_field": "routeName", "target_field": "route_name"},
        ]
        preview = await client.post(f"/api/v1/connectors/{connector_id}/mapping/preview", json={"sample": sample.json()["rows"][0], "mappings": mappings})
        preview.raise_for_status()
        assert preview.json()["transformed"]["status"] == "IN_TRANSIT"
        saved = await client.put(f"/api/v1/connectors/{connector_id}/mappings", json={"mappings": mappings})
        saved.raise_for_status()
        tracking = await client.put(f"/api/v1/connectors/{connector_id}/tracking-mapping", json={"source_field": "trackingEvents", "fields": [
            {"source_field": "id", "target_field": "external_event_id"},
            {"source_field": "event_type", "target_field": "event_type"},
            {"source_field": "location", "target_field": "location"},
            {"source_field": "event_time", "target_field": "event_time", "required": True},
        ]})
        tracking.raise_for_status()

        async def sync() -> dict:
            response = await client.post(f"/api/v1/connectors/{connector_id}/sync-jobs")
            response.raise_for_status()
            job_id = response.json()["id"]
            for _ in range(100):
                job = await client.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{job_id}")
                job.raise_for_status()
                if job.json()["status"] not in {"PENDING", "RUNNING"}:
                    return job.json()
                await asyncio.sleep(0.2)
            raise AssertionError("Sync job did not finish within 20 seconds")

        first = await sync()
        assert first["status"] == "SUCCESS" and first["result"]["imported"] == 25
        assert first["result"]["drivers_created"] and first["result"]["vehicles_created"]
        assert first["result"]["tracking_events_created"] == 25
        second = await sync()
        assert second["result"]["updated"] == 25 and second["result"]["tracking_events_created"] == 0
        shipments = await client.get("/api/v1/shipments", params={"search": prefix, "limit": 30})
        shipments.raise_for_status()
        assert shipments.json()["total"] == 25

        async def change_scenario(scenario: str) -> None:
            changed = await client.put(f"/api/v1/connectors/{connector_id}", json={"name": f"验收 TMS {prefix}", "type": "rest",
                "base_url": source_url + f"&scenario={scenario}", "auth_type": "none", "config": {}})
            changed.raise_for_status()

        await change_scenario("updated")
        updated = await sync()
        assert updated["status"] == "SUCCESS" and updated["result"]["updated"] == 25
        shipment_id = next(item["id"] for item in shipments.json()["items"] if item["shipment_no"] == f"{prefix}000001")
        detail = await client.get(f"/api/v1/shipments/{shipment_id}")
        detail.raise_for_status()
        assert detail.json()["status"] == "DELIVERED"
        assert detail.json()["source_connector"]["id"] == connector_id
        assert detail.json()["raw_data"] and detail.json()["last_synced_at"]
        assert len(detail.json()["tracking_events"]) == 1

        await change_scenario("messy")
        messy = await sync()
        assert messy["status"] == "PARTIAL_SUCCESS" and messy["failed_count"] >= 1
        issues = await client.get(f"/api/v1/connectors/{connector_id}/sync-jobs/{messy['id']}/issues")
        issues.raise_for_status()
        assert any(item["level"] == "ERROR" for item in issues.json())
        await change_scenario("default")
        print({"connector_id": connector_id, "first": first["result"]["imported"], "repeat_events": second["result"]["tracking_events_created"],
               "updated": updated["result"]["updated"], "partial_failures": messy["failed_count"], "issues": len(issues.json())})


if __name__ == "__main__":
    asyncio.run(main())
