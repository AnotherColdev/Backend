from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AuditLogCreate(BaseModel):
    service_name: str
    action: str
    user_id: Optional[str] = None
    details: Optional[str] = None

class AuditLogResponse(AuditLogCreate):
    id: int
    trace_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
