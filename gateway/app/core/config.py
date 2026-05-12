from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "API Gateway"
    MS_CONFIGURATION_URL: str = "http://ms-configuration:8003"
    MS_INGESTION_URL: str = "http://ms-ingestion:8001"
    MS_AUDIT_TRACE_URL: str = "http://ms-audit-trace:8002"
    MS_TRANSFORMATION_URL: str = "http://ms-transformation:8004"
    MS_ANALYTICS_URL: str = "http://ms-analytics:8005"
    MS_AUTH_URL: str = "http://ms-auth:8006"
    SECRET_KEY: str = "7963625368a52994073361e699f7d3c907727142b474e2a87474a87a747"
    ALGORITHM: str = "HS256"

settings = Settings()
