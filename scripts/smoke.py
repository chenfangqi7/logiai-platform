"""Run the MVP demo chain against a running Docker environment.

Usage: python scripts/smoke.py (with httpx installed and DEV_ADMIN_PASSWORD set)
"""

import asyncio
import os

import httpx


async def main() -> None:
    base = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8001")
    password = os.getenv("DEV_ADMIN_PASSWORD", "change-this-development-password")
    async with httpx.AsyncClient(base_url=base, timeout=30) as client:
        health = (await client.get("/health")).json()
        login = await client.post("/api/v1/auth/login", json={"tenant_code": "demo", "username": "admin", "password": password})
        login.raise_for_status()
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        existing = await client.get("/api/v1/connectors")
        existing.raise_for_status()
        connector = next((item for item in existing.json() if item["name"] == "Smoke TMS"), None)
        if connector is None:
            created = await client.post("/api/v1/connectors", json={"name": "Smoke TMS", "type": "rest", "base_url": "http://server:8000/demo/tms/shipments"})
            created.raise_for_status()
            connector = created.json()
        connector_id = connector["id"]
        sample = await client.post(f"/api/v1/connectors/{connector_id}/sample")
        sample.raise_for_status()
        mapping = {
            "waybillNo": "shipment_no", "status": "status", "fromArea": "origin", "toArea": "destination",
            "sendName": "sender_name", "receiveName": "receiver_name", "planDepart": "planned_departure_time",
            "actualDepart": "actual_departure_time", "planArrive": "planned_arrival_time",
            "driverCode": "driver_external_id", "plateNo": "vehicle_plate_no", "routeName": "route_name",
        }
        saved = await client.put(f"/api/v1/connectors/{connector_id}/mappings", json={"mappings": [
            {"source_field": source, "target_field": target, "required": target == "shipment_no"}
            for source, target in mapping.items()
        ]})
        saved.raise_for_status()
        synced = await client.post(f"/api/v1/connectors/{connector_id}/sync")
        synced.raise_for_status()
        imported = synced.json()
        shipments = await client.get("/api/v1/shipments", params={"search": "MOCK", "limit": 30})
        shipments.raise_for_status()
        exceptions = await client.get("/api/v1/exceptions", params={"limit": 5})
        exceptions.raise_for_status()
        ai = await client.post("/api/v1/ai/chat", json={"message": "帮我分析今天的异常运输情况。"})
        ai.raise_for_status()
        dashboard = await client.get("/api/v1/dashboard/overview")
        dashboard.raise_for_status()
        documents = await client.get("/api/v1/knowledge")
        documents.raise_for_status()
        if not any(item["title"] == "演示 SOP" for item in documents.json()):
            knowledge = await client.post("/api/v1/knowledge/text", json={"title": "演示 SOP", "content": "运输延误异常处理：联系司机确认位置，再通知客户预计到达时间。"})
            knowledge.raise_for_status()
        searched = await client.get("/api/v1/knowledge/search", params={"q": "运输延误异常处理"})
        searched.raise_for_status()
        print({
            "health": health["status"], "sample_fields": len(sample.json()["fields"]),
            "import": imported, "mock_shipments": shipments.json()["total"],
            "exceptions": exceptions.json()["total"], "ai_provider": ai.json()["provider"],
            "ai_answer": ai.json()["answer"], "dashboard": dashboard.json()["exception_count"],
            "knowledge_hits": len(searched.json()),
        })


if __name__ == "__main__":
    asyncio.run(main())
