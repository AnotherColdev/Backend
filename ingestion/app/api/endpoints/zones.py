from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.schemas.schema import ZoneListResponse
from app.services.zone_service import zone_service

router = APIRouter(tags=["Zonas"])


@router.get(
    "/zones",
    response_model=ZoneListResponse,
    summary="Consultar zonas disponibles",
    description="Retorna zonas de datasets válidos. Soporta paginación y filtro por dataset.",
)
def get_zones(
    dataset_id: Optional[str] = Query(
        None,
        description="ID del dataset. Si no se envía, retorna zonas de todos los datasets válidos."
    ),
    limit: int = Query(50, ge=1, le=200, description="Zonas por página (máximo 200)"),
    offset: int = Query(0, ge=0, description="Desde qué posición empezar"),
):
    
    result = zone_service.get_zones(
        dataset_id=dataset_id,
        limit=limit,
        offset=offset,
    )

    if result["total"] == 0:
        raise HTTPException(
            status_code=404,
            detail="No hay datasets válidos cargados aún"
        )

    return ZoneListResponse(
        success=True,
        total=result["total"],
        limit=limit,
        offset=offset,
        has_more=result["has_more"],
        data=result["zones"],
        error=None,
    )