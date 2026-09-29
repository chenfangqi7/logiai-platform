from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings

router = APIRouter(tags=["demo"])


@router.get("/demo/tms/shipments")
async def mock_tms_shipments(scenario: Literal["default", "updated", "messy"] = "default", prefix: str = Query("MOCK", min_length=1, max_length=12, pattern="^[A-Z0-9]+$"), fresh_relations: bool = False) -> list[dict]:
    if get_settings().app_env != "development":
        raise HTTPException(404, "Not found")
    now = datetime.now(timezone.utc)
    rows = []
    for number in range(1, 26):
        delay = number % 4 == 0
        tracking = now - timedelta(hours=6 if number % 5 == 0 else 1)
        route_name = "重庆→秀山" if number % 3 else "重庆→万州"
        rows.append({
            "waybillNo": f"{prefix}{number:06d}",
            "status": 30,
            "fromArea": "重庆市巴南区",
            "toArea": "重庆市秀山县" if number % 3 else "重庆市万州区",
            "sendName": f"客户{number}",
            "receiveName": f"收件人{number}",
            "planDepart": (now - timedelta(hours=3)).isoformat(),
            "actualDepart": None if delay else (now - timedelta(hours=2, minutes=50)).isoformat(),
            "planArrive": (now - timedelta(minutes=45) if delay else now + timedelta(hours=4)).isoformat(),
            "driverCode": f"{prefix}D{number:03d}" if fresh_relations else f"DRV{number % 30 + 1:03d}",
            "plateNo": f"渝{prefix}{number:03d}" if fresh_relations else f"渝A{number % 50 + 1:05d}",
            "routeName": f"{prefix if fresh_relations else ''}{route_name}",
            "trackingEvents": [{"id": f"{prefix}{number:06d}-TRACK-1", "event_type": "LOCATION", "location": "重庆", "event_time": tracking.isoformat()}],
        })
    if scenario == "updated":
        rows[0]["status"] = 40
        rows[0]["updatedAt"] = now.isoformat()
    if scenario == "messy":
        rows[1].pop("driverCode")
        rows[2].pop("plateNo")
        rows[3]["status"] = 99
        rows[4]["planDepart"] = "bad-time"
        rows[5]["journey"] = {"events": [{"event": {"id": "NESTED-1"}, "at": tracking.isoformat(), "place": "重庆"}]}
        rows[5].pop("trackingEvents")
        rows.append(dict(rows[0]))
    return rows
