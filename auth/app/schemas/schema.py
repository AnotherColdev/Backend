from pydantic import BaseModel
from typing import Optional

class HealthResponse(BaseModel):
    status: str
    service_name: str
    version: str
    db_connected: bool
    timestamp: str
