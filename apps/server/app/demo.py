from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings

router = APIRouter(tags=["demo"])


@router.get("/demo/tms/shipments")
async def mock_tms_shipments() -> list[dict]:
    if get_settings().app_env != "development":
        raise HTTPException(404, "Not found")
    now = datetime.now(timezone.utc)
    rows = []
    for number in range(1, 26):
        delay = number % 4 == 0
        tracking = now - timedelta(hours=6 if number % 5 == 0 else 1)
        rows.append({
            "waybillNo": f"MOCK{number:06d}",
            "status": 30,
            "fromArea": "重庆市巴南区",
            "toArea": "重庆市秀山县" if number % 3 else "重庆市万州区",
            "sendName": f"客户{number}",
            "receiveName": f"收件人{number}",
            "planDepart": (now - timedelta(hours=3)).isoformat(),
            "actualDepart": None if delay else (now - timedelta(hours=2, minutes=50)).isoformat(),
            "planArrive": (now - timedelta(minutes=45) if delay else now + timedelta(hours=4)).isoformat(),
            "driverCode": f"DRV{number % 30 + 1:03d}",
            "plateNo": f"渝A{number % 50 + 1:05d}",
            "routeName": "重庆→秀山" if number % 3 else "重庆→万州",
            "trackingEvents": [{"event_type": "LOCATION", "location": "重庆", "event_time": tracking.isoformat()}],
        })
    return rows
