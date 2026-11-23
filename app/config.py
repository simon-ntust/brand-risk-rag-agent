from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/brand_risk"
    openai_api_key: str = "test-key"
    openai_base_url: str | None = None
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-08-01-preview"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()