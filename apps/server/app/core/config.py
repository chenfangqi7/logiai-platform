from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "LogiAI Platform"
    database_url: str = "postgresql+asyncpg://logiai:logiai@localhost:5432/logiai"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-replace-before-deployment"
    jwt_expire_minutes: int = 1440
    dev_tenant_code: str = "demo"
    dev_tenant_name: str = "演示租户"
    dev_admin_username: str = "admin"
    dev_admin_email: str = "admin@example.local"
    dev_admin_password: str = "change-this-development-password"
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_input_cost_per_million: float = 0.0
    llm_output_cost_per_million: float = 0.0
    embedding_provider: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
