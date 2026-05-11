from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.transform_schema import TransformRequest, SuccessResponse
from app.services.transformer_service import TransformerService
import uuid

router = APIRouter(prefix="/api/v1")

@router.post("/transform", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def transform_dataset(request: TransformRequest, db: Session = Depends(get_db)):
    """
    Inicia la transformación de datos para un dataset validado.
    """
    service = TransformerService(db)
    
    try:
        result = await service.transform(request.dataset_load_id)
        
        return SuccessResponse(
            success=True,
            data=result,
            trace_id=str(uuid.uuid4())
        )
    except ValueError as e:
        # Invalid dataset id
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected error
        raise HTTPException(status_code=500, detail=str(e))
