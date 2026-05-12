from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {'schema': 'audit_trace'}

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String, index=True)
    service_name = Column(String, index=True)
    action = Column(String)
    user_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
