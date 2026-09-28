import httpx

from app.ai.gateway.llm import Generation
from app.core.config import get_settings


class OpenAICompatibleProvider:
    async def generate(self, system: str, user: str) -> Generation:
        settings = get_settings()
        if not settings.llm_api_key or not settings.llm_model:
            raise ValueError("LLM is not configured")
        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.llm_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
            response.raise_for_status()
        result = response.json()
        usage = result.get("usage") or {}
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content:
            raise ValueError("LLM returned no text")
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        cost = (input_tokens * settings.llm_input_cost_per_million + output_tokens * settings.llm_output_cost_per_million) / 1_000_000
        return Generation(text=content, provider=settings.llm_provider or "openai-compatible", model=result.get("model", settings.llm_model),
            input_tokens=input_tokens, output_tokens=output_tokens, cost=cost)
