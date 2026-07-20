from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ResumeParser.AI"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    # For local development we fall back to SQLite when DATABASE_URL is not provided.
    # In production, set DATABASE_URL to a Postgres connection string.
    database_url: str = "sqlite:///./dev.db"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_url: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@resumeparser.ai"
    admin_email: str = "admin@example.com"
    admin_password: str = ""
    ats_shortlist_threshold: float = 70.0
    upload_root: str = ""
    frontend_hostname: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
