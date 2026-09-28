import pytest
from app.models.domain import AIUsage
from test_connector_import import token


@pytest.mark.asyncio
async def test_ai_usage_dashboard_and_tenant_isolation(client):
    http, first_id, second_id, _ = client
    first = await token(http, "first", "correct-password")
    second = await token(http, "second", "second-password")

    # 1. 查询初始看板
    res_first = await http.get("/api/v1/ai/usage/dashboard", headers=first)
    assert res_first.status_code == 200
    data_first = res_first.json()
    assert "summary" in data_first
    assert "trend" in data_first
    assert "distribution_by_purpose" in data_first
    assert "distribution_by_model" in data_first
    assert "models_info" in data_first
    assert "recent_logs" in data_first
    assert data_first["summary"]["total_calls"] == 0

    # 2. 模拟第一租户发起 AI 对话，产生用量记录
    chat_res = await http.post("/api/v1/ai/chat", headers=first, json={"message": "今天有多少异常运单？"})
    assert chat_res.status_code == 200

    # 3. 再次查询第一租户的用量看板
    after_first = (await http.get("/api/v1/ai/usage/dashboard", headers=first)).json()
    assert after_first["summary"]["total_calls"] >= 1
    assert len(after_first["recent_logs"]) >= 1
    assert after_first["recent_logs"][0]["purpose"] == "chat"

    # 4. 验证租户隔离：第二租户看不到第一租户的用量
    after_second = (await http.get("/api/v1/ai/usage/dashboard", headers=second)).json()
    assert after_second["summary"]["total_calls"] == 0
    assert len(after_second["recent_logs"]) == 0

    # 5. 测试 logs 分页接口
    logs_res = await http.get("/api/v1/ai/usage/logs?limit=10&offset=0", headers=first)
    assert logs_res.status_code == 200
    assert logs_res.json()["total"] >= 1
    assert len(logs_res.json()["items"]) >= 1
