from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "ApprovalFlow Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8001
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./approvalflow.db"

    # Security
    API_KEY: str = "test-admin-secret-key"
    REQUIRE_AUTH: bool = False  # Allows easy zero-friction local testing when false, or set true for strict auth

    # External Sandbox / Communication Provider
    EMAIL_PROVIDER: str = "sandbox"  # 'sandbox' or 'smtp'
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "agent@approvalflow.internal"

    # LLM Settings
    LLM_PROVIDER: str = "heuristic"  # 'heuristic', 'openai', 'anthropic', 'gemini'
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
