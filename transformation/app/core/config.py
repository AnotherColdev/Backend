import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuración del microservicio de transformación.
    Las variables se leen del entorno o del archivo .env.
    """
    PROJECT_NAME: str = "Transformation Service"
    SERVICE_VERSION: str = "1.0.0"

    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "admin")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db_postgres")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "territorial_db")

    # Storage path (shared volume with ingestion service)
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "/app/storage")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
