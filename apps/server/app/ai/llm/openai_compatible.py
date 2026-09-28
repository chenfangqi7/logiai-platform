import httpx

from app.ai.gateway.llm import Generation
from app.core.config import get_settings


class OpenAICompatibleProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider_name: str | None = None,
        input_cost: float | None = None,
        output_cost: float | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.provider_name = provider_name
        self.input_cost = input_cost
        self.output_cost = output_cost

    async def generate(self, system: str, user: str) -> Generation:
        settings = get_settings()
        api_key = self.api_key or settings.llm_api_key
        model = self.model or settings.llm_model
        base_url = self.base_url or settings.llm_base_url
        provider_name = self.provider_name or settings.llm_provider or "openai-compatible"
        input_cost_rate = self.input_cost if self.input_cost is not None else settings.llm_input_cost_per_million
        output_cost_rate = self.output_cost if self.output_cost is not None else settings.llm_output_cost_per_million

        if not api_key or not model:
            raise ValueError("LLM is not configured")
        url = base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
            response.raise_for_status()
        result = response.json()
        usage = result.get("usage") or {}
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content:
            raise ValueError("LLM returned no text")
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        cost = (input_tokens * input_cost_rate + output_tokens * output_cost_rate) / 1_000_000
        return Generation(
            text=content,
            provider=provider_name,
            model=result.get("model", model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
