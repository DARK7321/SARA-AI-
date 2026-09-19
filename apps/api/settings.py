from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GEMINI_API_KEY: str = ''
    APP_ENV: str = 'dev'
    APP_NAME: str = 'OmniBrain'
    DEBUG: bool = True
    LOG_LEVEL: str = 'INFO'
    OWNER_EMAIL: str = 'admin@omnibrain.local'
    OWNER_PASSWORD: str = 'OmniBrain@2026'
    GOOGLE_CLIENT_ID: str = 'mock-google-client-id'
    GOOGLE_CLIENT_SECRET: str = 'mock-google-secret'

    model_config = SettingsConfigDict(env_file='.env', extra='allow')

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "debug", "dev")
        return bool(v)

@lru_cache
def get_settings():
    return Settings()
