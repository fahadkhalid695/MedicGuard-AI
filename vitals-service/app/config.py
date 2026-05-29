from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://mediguard:password@localhost:5432/mediguard"
    redis_url: str = "redis://localhost:6379/0"
    vitals_cache_ttl: int = 60  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
