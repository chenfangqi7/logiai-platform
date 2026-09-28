from types import SimpleNamespace

import pytest

from app.ai.gateway.llm import Generation
from app.ai.llm.openai_compatible import OpenAICompatibleProvider
from app.services.connector import ConnectorService
from test_connector_import import token


@pytest.mark.asyncio
async def test_exception_analysis_uses_tenant_data_and_persists_model_output(client, monkeypatch):
    http, _, _, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")
    connector = await http.post("/api/v1/connectors", headers=first, json={"name": "TMS", "type": "rest", "base_url": "http://localhost:8000/demo/tms/shipments"})
    connector_id = connector.json()["id"]
    await http.put(f"/api/v1/connectors/{connector_id}/mappings", headers=first, json={"mappings": [{"source_field": "waybillNo", "target_field": "shipment_no", "required": True}]})

    async def fake_fetch(self, item, sample=False):
        return [{"waybillNo": "YD-ANALYZE"}]

    async def fake_generate(self, system, user):
        assert "YD-ANALYZE" in user
        return Generation(text='{"analysis":"车辆资料缺失，影响运输监控。","suggestion":"补录车辆和司机信息。"}', provider="test-llm", model="test-model", input_tokens=20, output_tokens=10)

    monkeypatch.setattr(ConnectorService, "fetch", fake_fetch)
    monkeypatch.setattr(OpenAICompatibleProvider, "generate", fake_generate)
    monkeypatch.setattr("app.services.exception_analysis.get_settings", lambda: SimpleNamespace(llm_api_key="test", llm_model="test-model"))
    imported = await http.post(f"/api/v1/connectors/{connector_id}/sync", headers=first)
    exception_id = imported.json()["exception_ids"][0]
    assert (await http.post(f"/api/v1/exceptions/{exception_id}/analyze", headers=second)).status_code == 404
    analyzed = await http.post(f"/api/v1/exceptions/{exception_id}/analyze", headers=first)
    assert analyzed.status_code == 200, analyzed.text
    assert analyzed.json()["ai_analysis"] == "车辆资料缺失，影响运输监控。"
    assert analyzed.json()["suggestion"] == "补录车辆和司机信息。"
