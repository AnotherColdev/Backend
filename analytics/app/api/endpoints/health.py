from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from app.core.database import get_db
from app.core.config import settings
from app.schemas.schema import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_connected = _check_db(db)
    data = HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        service_name=settings.service_name,
        version=settings.service_version,
        db_connected=db_connected,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    if not db_connected:
        return JSONResponse(status_code=503, content=data.model_dump())
    return data


def _check_db(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False