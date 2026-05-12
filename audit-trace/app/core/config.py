import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Usar SQLite por defecto (archivo local, no necesita servidor)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./audit_trace.db")
    SERVICE_NAME: str = "audit-trace"
    VERSION: str = "1.0.0"
    
    class Config:
        extra = "ignore"

settings = Settings()