from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ProcessTrace(Base):
    __tablename__ = "process_traces"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_load_id = Column(String(100), nullable=False, index=True)
    transformation_run_id = Column(String(100), nullable=True)
    score_execution_id = Column(String(100), nullable=True)
    event_type = Column(String(50), nullable=False)
    status = Column(String(20), default="success")
    parameters = Column(JSON, nullable=True)
    result_summary = Column(JSON, nullable=True)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)