from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    app_name: str = "QShield"
    app_version: str = "0.1.0"

    # Database
    database_url: str = "sqlite:///./qshield.db"

    # Upload
    max_upload_size_mb: int = 10
    allowed_extensions: str = (
        ".py,.js,.ts,.java,.go,.rb,.php,.c,.cpp,.h,.cs,"
        ".yaml,.yml,.json,.toml,.ini,.conf,.env,.pem,.crt,.cer,.der"
    )

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Optional AI layer
    openai_api_key: str = ""

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
