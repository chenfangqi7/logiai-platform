import httpx

from app.ai.gateway.llm import Generation
from app.core.config import get_settings


class AnthropicMessagesProvider:
    async def generate(self, system: str, user: str) -> Generation:
        settings = get_settings()
        if not settings.llm_api_key or not settings.llm_model:
            raise ValueError("LLM is not configured")
        url = settings.llm_base_url.rstrip("/") + "/v1/messages"
        headers = {
            "x-api-key": settings.llm_api_key,
            "Authorization": f"Bearer {settings.llm_api_key}",
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": settings.llm_model,
            "max_tokens": 2048,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        result = response.json()
        content = "\n".join(block.get("text", "") for block in result["content"] if block.get("type") == "text").strip()
        if not content:
            raise ValueError("LLM returned no text")
        usage = result.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        cost = (input_tokens * settings.llm_input_cost_per_million + output_tokens * settings.llm_output_cost_per_million) / 1_000_000
        return Generation(text=content, provider="anthropic-messages", model=result.get("model", settings.llm_model),
            input_tokens=input_tokens, output_tokens=output_tokens, cost=cost)
