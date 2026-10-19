from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WHATSIZE_", env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+psycopg://whatsize:whatsize@localhost:5432/whatsize"
    redis_url: str = "redis://localhost:6379/0"
    # Comma-separated list of allowed browser origins (the Flutter web build).
    cors_origins: str = "*"
    # Run Alembic migrations and load the reference seed on startup. On for the
    # test environment (Render has no pre-deploy step on the free tier).
    auto_migrate: bool = False
    # Serve the bundled reference seed from memory if the database is unreachable.
    reference_fallback: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
