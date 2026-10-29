from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_name: str = "DIGITAL Intelligent Criminal Scene Investigation API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./criminal_scene.db"
    jwt_secret_key: str = "change-this-development-secret-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    app_env: str = "development"
    storage_root: str = "./storage"
    max_upload_size_bytes: int = 1073741824
    pdal_path: str = "pdal"
    potree_converter_path: str = "PotreeConverter"
    conversion_timeout_seconds: int = 3600
    redis_url: str = "redis://localhost:6379/0"
    rq_queue_name: str = "pointcloud"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
