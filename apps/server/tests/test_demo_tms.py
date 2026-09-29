import pytest


@pytest.mark.asyncio
async def test_demo_tms_exposes_reproducible_event_ids_and_messy_cases(client):
    http, _, _, _ = client
    default = (await http.get("/demo/tms/shipments")).json()
    assert len(default) == 25
    assert default[0]["trackingEvents"][0]["id"] == "MOCK000001-TRACK-1"
    updated = (await http.get("/demo/tms/shipments?scenario=updated")).json()
    assert updated[0]["status"] == 40
    messy = (await http.get("/demo/tms/shipments?scenario=messy")).json()
    assert len(messy) == 26
    assert "driverCode" not in messy[1] and "plateNo" not in messy[2]
    assert messy[3]["status"] == 99 and messy[4]["planDepart"] == "bad-time"
    assert messy[5]["journey"]["events"]
    prefixed = (await http.get("/demo/tms/shipments?prefix=ACPT")).json()
    assert prefixed[0]["waybillNo"] == "ACPT000001"
    fresh = (await http.get("/demo/tms/shipments?prefix=ACPT&fresh_relations=true")).json()
    assert fresh[0]["driverCode"].startswith("ACPT") and fresh[0]["plateNo"].startswith("渝ACPT")
