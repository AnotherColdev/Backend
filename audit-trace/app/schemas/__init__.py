from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ProcessTraceCreate(BaseModel):
    dataset_load_id: str
    transformation_run_id: Optional[str] = None
    score_execution_id: Optional[str] = None
    event_type: str
    status: str = "success"
    parameters: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class TraceChainResponse(BaseModel):
    dataset_load_id: str
    timeline: Dict[str, Any]