from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.schema import RankingResponse
from app.repositories.ranking_repository import RankingRepository
from app.services.ranking_service import RankingService

router = APIRouter(tags=["Ranking"])


def _get_ranking_service(db: Session = Depends(get_db)) -> RankingService:
    """
    DIP: el endpoint nunca conoce RankingRepository directamente.
    """
    repository = RankingRepository(db)
    return RankingService(repository)


@router.get(
    "/ranking",
    response_model=RankingResponse,
    summary="Ranking de zonas por score",
    description=(
        "Retorna zonas ordenadas de mayor a menor score. "
        "Soporta filtro por nivel (ALTA/MEDIA/BAJA) y paginación de 20 por página."
    ),
)
def get_ranking(
    execution_id: str = Query(
        ...,
        description="ID de la ejecución de scoring a consultar"
    ),
    level: Optional[str] = Query(
        None,
        description="Filtrar por nivel: ALTA, MEDIA o BAJA"
    ),
    page: int = Query(1, ge=1, description="Número de página (inicia en 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Resultados por página"),
    service: RankingService = Depends(_get_ranking_service),
):
    
    try:
        if level:
            level = level.upper()
        return service.get_ranking(
            execution_id=execution_id,
            level=level,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))