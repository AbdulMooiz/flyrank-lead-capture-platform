from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://flyrank:flyrank@localhost:5432/flyrank"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "local-development-secret-change-me"
    access_token_expire_minutes: int = 60
    api_base_url: str = "http://localhost:8000"
    customer_origins: str = "http://localhost:5500"
    max_body_bytes: int = 32768
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60
    geo_timeout_seconds: float = 3.0
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.customer_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
