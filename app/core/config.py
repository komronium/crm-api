from typing import List

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "CRM API"
    PROJECT_VERSION: str = "0.0.1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: PostgresDsn
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Business timezone (dashboard days, stats): leads are counted by the local day, not by UTC
    TIMEZONE: str = "Asia/Tashkent"

    # Authentication
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCK_SECONDS: int = 900

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8000"]

    # Facebook / Meta Graph API (Lead Ads import)
    FACEBOOK_GRAPH_VERSION: str = "v25.0"
    FACEBOOK_ACCESS_TOKEN: SecretStr | None = None
    FACEBOOK_LEADGEN_FORM_ID: str | None = None
    FACEBOOK_WEBHOOK_VERIFY_TOKEN: SecretStr | None = None
    FACEBOOK_PAGE_ID: str | None = None
    FACEBOOK_POLL_INTERVAL_SECONDS: int = 60
    FACEBOOK_POLL_LOOKBACK_SECONDS: int = 86400
    FACEBOOK_IMPORT_LIMIT_PER_FORM: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
