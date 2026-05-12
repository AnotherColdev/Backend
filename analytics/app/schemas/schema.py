from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ScoreLevel(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"

class ZoneRankingItem(BaseModel):
    rank_position: int
    zone_code: str
    zone_name: str
    score_value: float
    score_level: ScoreLevel
    execution_id: str

class RankingResponse(BaseModel):
    success: bool
    execution_id: str
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    level_filter: Optional[str]
    data: List[ZoneRankingItem]
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service_name: str
    version: str
    db_connected: bool
    timestamp: str