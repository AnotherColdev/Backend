from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class TransformRequest(BaseModel):
    dataset_load_id: str = Field(..., description="ID del dataset cargado provisto por ms-ingestion")

class TransformResponse(BaseModel):
    transformation_run_id: str
    total_zones_processed: int
    rules_applied: List[str]
    output_version: str

# Standard JSON response schemas
class SuccessResponse(BaseModel):
    success: bool = True
    data: TransformResponse
    error: Optional[str] = None
    trace_id: Optional[str] = None
