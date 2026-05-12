from pydantic import BaseModel
from typing import Optional, List


class ZoneItem(BaseModel):
    zone_code: str
    zone_name: str


class ZoneListResponse(BaseModel):
    success: bool
    total: int
    limit: int
    offset: int
    has_more: bool         #True si hay más zonas después de esta página
    data: List[ZoneItem]
    error: Optional[str]