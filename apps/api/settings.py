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

    model_config = SettingsConfigDict(env_file='.env')

@lru_cache
def get_settings():
    return Settings()
