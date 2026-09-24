from typing import Any
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = 'postgresql+asyncpg://postgres.cyyyovignjkxvhzfitux:734029%40Vikas@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres'
    REDIS_URL: str = 'redis://localhost:6379/0'
    JWT_SECRET_KEY: str = Field(default='change-me-in-production-use-a-long-random-string', validation_alias=AliasChoices('JWT_SECRET_KEY', 'JWT_SECRET'))
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GEMINI_API_KEY: str = 'AQ.Ab8RN6ILMgS-iwdMPgmu5e4Iy2cthrMvft2X-i0ZonNjovg2bA'
    APP_ENV: str = 'dev'
    APP_NAME: str = 'OmniBrain'
    DEBUG: bool = True
    LOG_LEVEL: str = 'INFO'
    OWNER_EMAIL: str = 'vikas635026@gmail.com'
    OWNER_PASSWORD: str = 'OmniBrain@2026'
    GOOGLE_CLIENT_ID: str = '279884272633-h83038hv52ovkk2r35tne2nbqofnqv0f.apps.googleusercontent.com'
    GOOGLE_CLIENT_SECRET: str = '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'
    OMNIBRAIN_HOST_JWT_SECRET: str = 'OMNIBRAIN_HOST_JWT_SECRET_DEV_KEY'
    OMNIBRAIN_HOST_ALLOWED_ROOTS: str = '~/Desktop;~/Documents;~/Downloads'

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
