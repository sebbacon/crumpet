from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./markdown.db"
    api_key: str = "dev_api_key"

def get_settings():
    return Settings()
