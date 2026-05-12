import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "ms-analytics"
    service_version: str = "1.0.0"
    service_port: int = 8005
    environment: str = "dev"
    
    # Database settings
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "admin")
    postgres_host: str = os.getenv("POSTGRES_HOST", "db-postgres")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "territorial_db")

    database_url: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if not self.database_url:
            self.database_url = f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()