import logging

from app.ai.gateway.llm import Generation, LLMProvider
from app.ai.llm.anthropic_messages import AnthropicMessagesProvider
from app.ai.llm.openai_compatible import OpenAICompatibleProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ResilientLLMProvider:
    """Wrapper that tries primary LLM provider first, and falls back to backup provider upon error or timeout."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback

    async def generate(self, system: str, user: str) -> Generation:
        if self.fallback is None:
            return await self.primary.generate(system, user)
        try:
            return await self.primary.generate(system, user)
        except Exception as exc:
            logger.warning("Primary LLM request failed (%s). Falling back to backup LLM provider.", exc)
            return await self.fallback.generate(system, user)


def create_single_provider(
    provider_type: str,
    api_key: str,
    base_url: str,
    model: str,
    input_cost: float,
    output_cost: float,
) -> LLMProvider:
    p = provider_type.lower().strip()
    if p in {"anthropic", "anthropic-messages"}:
        return AnthropicMessagesProvider()
    if p in {"", "openai", "openai-compatible", "qwen", "deepseek", "ollama"}:
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider_name=provider_type or "openai-compatible",
            input_cost=input_cost,
            output_cost=output_cost,
        )
    raise ValueError(f"Unsupported LLM provider: {provider_type}")


def is_llm_configured(settings=None) -> bool:
    if settings is None:
        settings = get_settings()
    has_primary = bool(getattr(settings, "llm_api_key", None) and getattr(settings, "llm_model", None))
    has_fallback = bool(getattr(settings, "fallback_llm_api_key", None) and getattr(settings, "fallback_llm_model", None))
    return has_primary or has_fallback


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    primary = create_single_provider(
        provider_type=getattr(settings, "llm_provider", ""),
        api_key=getattr(settings, "llm_api_key", ""),
        base_url=getattr(settings, "llm_base_url", "https://api.openai.com/v1"),
        model=getattr(settings, "llm_model", ""),
        input_cost=getattr(settings, "llm_input_cost_per_million", 0.0),
        output_cost=getattr(settings, "llm_output_cost_per_million", 0.0),
    )

    fallback_key = getattr(settings, "fallback_llm_api_key", "")
    fallback_model = getattr(settings, "fallback_llm_model", "")
    if not fallback_key or not fallback_model:
        return primary

    fallback = create_single_provider(
        provider_type=getattr(settings, "fallback_llm_provider", "qwen") or "qwen",
        api_key=fallback_key,
        base_url=getattr(settings, "fallback_llm_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        model=fallback_model,
        input_cost=getattr(settings, "fallback_llm_input_cost_per_million", 0.0),
        output_cost=getattr(settings, "fallback_llm_output_cost_per_million", 0.0),
    )

    return ResilientLLMProvider(primary=primary, fallback=fallback)

