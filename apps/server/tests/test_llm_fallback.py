import httpx
import pytest

from app.ai.gateway.llm import Generation, LLMProvider
from app.ai.gateway.provider import ResilientLLMProvider, get_llm_provider
from app.core.config import Settings


class MockProvider:
    def __init__(self, name: str, should_fail: bool = False, fail_exc: Exception | None = None) -> None:
        self.name = name
        self.should_fail = should_fail
        self.fail_exc = fail_exc or httpx.ConnectError("Network unreachable")
        self.call_count = 0

    async def generate(self, system: str, user: str) -> Generation:
        self.call_count += 1
        if self.should_fail:
            raise self.fail_exc
        return Generation(text=f"Response from {self.name}", provider=self.name, model="test-model")


@pytest.mark.asyncio
async def test_resilient_provider_uses_primary_when_available():
    primary = MockProvider("primary")
    fallback = MockProvider("fallback")
    provider = ResilientLLMProvider(primary=primary, fallback=fallback)

    res = await provider.generate("system", "user")
    assert res.text == "Response from primary"
    assert primary.call_count == 1
    assert fallback.call_count == 0


@pytest.mark.asyncio
async def test_resilient_provider_falls_back_on_primary_error():
    primary = MockProvider("primary", should_fail=True)
    fallback = MockProvider("fallback")
    provider = ResilientLLMProvider(primary=primary, fallback=fallback)

    res = await provider.generate("system", "user")
    assert res.text == "Response from fallback"
    assert primary.call_count == 1
    assert fallback.call_count == 1


@pytest.mark.asyncio
async def test_resilient_provider_falls_back_on_unconfigured_primary():
    primary = MockProvider("primary", should_fail=True, fail_exc=ValueError("LLM is not configured"))
    fallback = MockProvider("fallback")
    provider = ResilientLLMProvider(primary=primary, fallback=fallback)

    res = await provider.generate("system", "user")
    assert res.text == "Response from fallback"
    assert primary.call_count == 1
    assert fallback.call_count == 1


@pytest.mark.asyncio
async def test_get_llm_provider_wires_fallback(monkeypatch):
    test_settings = Settings(
        llm_provider="openai",
        llm_api_key="primary-key",
        llm_base_url="http://internal-lan:8000/v1",
        llm_model="internal-model",
        fallback_llm_provider="qwen",
        fallback_llm_api_key="fallback-key",
        fallback_llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        fallback_llm_model="qwen3.8-flash",
    )
    monkeypatch.setattr("app.ai.gateway.provider.get_settings", lambda: test_settings)

    provider = get_llm_provider()
    assert isinstance(provider, ResilientLLMProvider)
    assert provider.fallback is not None
    assert provider.fallback.api_key == "fallback-key"
    assert provider.fallback.model == "qwen3.8-flash"
