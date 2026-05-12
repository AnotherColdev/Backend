from fastapi import APIRouter, Depends, File, Request, UploadFile, Query, HTTPException, BackgroundTasks, Form
from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from app.api import deps
from app.core.audit_client import log_audit_action
from app.interfaces.ingestionService import IIngestionService
from app.interfaces.datasetRepo import IDatasetRepository
from app.schemas.dataset import DatasetResponse, ZoneListResponse
from app.api.deps import getDatasetRepository, getIngestionService

router = APIRouter()
logger = logging.getLogger("IngestionEndpoint")

@router.post("/upload", response_model=DatasetResponse)
async def uploadDataset(
    request: Request,
    file: UploadFile = File(...),
    sourceName: Optional[str] = Form(None),
    sourceType: Optional[str] = Form(None),
    ingestionService: IIngestionService = Depends(getIngestionService)
):
    trace_id = getattr(request.state, "trace_id", "Unknown")
    user_id = None
    if hasattr(request.state, "user"):
         user_id = str(request.state.user.get("sub"))
    
    try:
        dataset = await ingestionService.processUpload(
            userId=user_id or "anonymous",
            file=file,
            sourceName=sourceName,
            sourceType=sourceType
        )
        
        # Log success to audit
        await log_audit_action(
            action="UPLOAD_DATASET",
            details=f"Dataset '{dataset.fileName}' (id={dataset.datasetId}) cargado exitosamente.",
            user_id=user_id,
            trace_id=trace_id
        )
        
        return dataset
    except Exception as e:
        # Log failure to audit
        await log_audit_action(
            action="UPLOAD_DATASET_FAILED",
            details=f"Fallo al cargar {file.filename}: {str(e)}",
            user_id=user_id,
            trace_id=trace_id
        )
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[DatasetResponse])
def getDatasets(
    datasetRepo: IDatasetRepository = Depends(getDatasetRepository)
):
    return datasetRepo.getAll()

@router.get("/zones", response_model=ZoneListResponse)
def getZones(
    datasetId: Optional[str] = Query(None, description="Filtrar por datasetId"),
    search: Optional[str] = Query(None, description="Buscar por nombre o código"),
    department: Optional[str] = Query(None, description="Filtrar por departamento"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    datasetRepo: IDatasetRepository = Depends(getDatasetRepository)
):
    zones, total = datasetRepo.getZones(datasetId=datasetId, search=search, limit=limit, offset=offset, department=department)
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "zoneCode": z.zoneCode, 
                "zoneName": z.zoneName, 
                "department": z.department
            } for z in zones
        ]
    }

@router.get("/{id}", response_model=DatasetResponse)
def getDatasetById(
    id: str,
    datasetRepo: IDatasetRepository = Depends(getDatasetRepository)
):
    dataset = datasetRepo.getById(id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return dataset
