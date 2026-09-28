from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "LogiAI Platform"
    database_url: str = "postgresql+asyncpg://logiai:logiai@localhost:5432/logiai"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "sslmode=" in v:
                v = v.replace("sslmode=", "ssl=")
        return v
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-replace-before-deployment"
    connector_secret_key: str = ""
    jwt_expire_minutes: int = 1440
    dev_tenant_code: str = "demo"
    dev_tenant_name: str = "演示租户"
    dev_admin_username: str = "admin"
    dev_admin_email: str = "admin@example.local"
    dev_admin_password: str = "123456"
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_input_cost_per_million: float = 0.8
    llm_output_cost_per_million: float = 2.7
    fallback_llm_provider: str = "qwen"
    fallback_llm_api_key: str = ""
    fallback_llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    fallback_llm_model: str = "qwen3.8-flash"
    fallback_llm_input_cost_per_million: float = 0.8
    fallback_llm_output_cost_per_million: float = 2.7
    embedding_provider: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""

    @property
    def is_llm_enabled(self) -> bool:
        primary_enabled = bool(self.llm_api_key and self.llm_model)
        fallback_enabled = bool(self.fallback_llm_api_key and self.fallback_llm_model)
        return primary_enabled or fallback_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
