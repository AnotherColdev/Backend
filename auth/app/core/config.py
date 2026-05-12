import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Auth Service"
    service_name: str = "ms-auth"
    service_version: str = "1.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:admin@db-postgres:5432/territorial_db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "7963625368a52994073361e699f7d3c907727142b474e2a87474a87a747")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

settings = Settings()
