from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Ingestion Service"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "admin"
    POSTGRES_HOST: str = "db_postgres"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "territorial_db"
    JWT_SECRET: str = "supersecretkey12345"
    JWT_ALGORITHM: str = "HS256"
    STORAGE_PATH: str = "/app/storage"
    MS_AUDIT_TRACE_URL: str = "http://ms-audit-trace:8002"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
