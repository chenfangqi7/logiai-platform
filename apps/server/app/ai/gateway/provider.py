from app.ai.gateway.llm import LLMProvider
from app.ai.llm.anthropic_messages import AnthropicMessagesProvider
from app.ai.llm.openai_compatible import OpenAICompatibleProvider
from app.core.config import get_settings


def get_llm_provider() -> LLMProvider:
    provider = get_settings().llm_provider.lower().strip()
    if provider in {"anthropic", "anthropic-messages"}:
        return AnthropicMessagesProvider()
    if provider in {"", "openai", "openai-compatible"}:
        return OpenAICompatibleProvider()
    raise ValueError(f"Unsupported LLM provider: {provider}")
