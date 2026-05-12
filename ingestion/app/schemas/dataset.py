from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class DatasetResponse(BaseModel):
    id:                 int
    datasetId:          str
    userId:             str
    fileName:           str
    sourceName:         Optional[str] = None
    sourceType:         Optional[str] = None
    fileHash:           str
    fileSize:           int
    recordCount:        int
    validRecordCount:   int
    invalidRecordCount: int
    uploadedAt:         datetime
    status:             str

    class Config:
        from_attributes = True


class ZoneResponse(BaseModel):
    zoneCode: str
    zoneName: str
    department: Optional[str] = None

    class Config:
        from_attributes = True


class ZoneListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[ZoneResponse]
