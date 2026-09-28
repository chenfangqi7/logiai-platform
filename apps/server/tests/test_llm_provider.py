import httpx
import pytest

from app.ai.llm.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_provider_sends_grounded_messages_and_tracks_usage(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = __import__("json").loads(request.content)
        assert payload["model"] == "test-model"
        assert payload["messages"][0]["content"] == "Only facts"
        return httpx.Response(200, json={"model": "test-model", "choices": [{"message": {"content": "Grounded answer"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}})

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr("app.ai.llm.openai_compatible.httpx.AsyncClient", lambda **kwargs: real_client(transport=transport))
    monkeypatch.setattr("app.ai.llm.openai_compatible.get_settings", lambda: type("Settings", (), {
        "llm_api_key": "test-key", "llm_model": "test-model", "llm_provider": "openai-compatible",
        "llm_base_url": "https://api.example.test/v1", "llm_input_cost_per_million": 1.0,
        "llm_output_cost_per_million": 2.0,
    })())
    result = await OpenAICompatibleProvider().generate("Only facts", "Question and evidence")
    assert result.text == "Grounded answer"
    assert result.input_tokens == 100 and result.output_tokens == 50
    assert result.cost == pytest.approx(0.0002)
