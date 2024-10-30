from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Default to data directory in deployment, fall back to local directory for development
    database_url: str = "sqlite:///app/data/crumpet.db"
    api_key: str = "dev_api_key"

    class Config:
        env_file = ".env"
        extra = "ignore"


def get_settings():
    return Settings()
