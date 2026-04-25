"""
ms-transformation — Microservicio de Transformación Avanzada
=============================================================

Provee endpoints para transformar datasets ingestados aplicando:
  - Limpieza (imputación por mediana, deduplicación, estandarización)
  - Detección y Winsorización de outliers (±3σ → P1/P99)
  - Normalización (Min-Max o Z-Score)
  - Generación de reporte estadístico por columna

HU-20: Normalización Avanzada — Sprint 2
"""

import time
import uuid
import logging

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, get_db, init_db
from app.core.exceptions import DomainException, global_exception_handler
from app.schemas.schemas import TransformRequest, TransformResponse
from app.services.transformation_service import process_advanced_transformation

# ── Logging ──
logger = logging.getLogger("TransformationService")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - [Trace: %(trace_id)s] - %(message)s"
)
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

# ── App ──
app = FastAPI(
    title="Transformation Service",
    description="Microservicio de transformación y normalización avanzada de datos territoriales (HU-20)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)


# ── Middleware de trazabilidad ──
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    adapter = logging.LoggerAdapter(logger, {"trace_id": trace_id})
    request.state.logger = adapter

    adapter.info(f"Received: {request.method} {request.url.path}")
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    adapter.info(f"Response: {response.status_code}")
    return response


# ── Startup ──
@app.on_event("startup")
async def startup():
    init_db()


# ── Health & Root ──
@app.get("/health")
def health():
    try:
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "healthy" if db_connected else "unhealthy",
        "service": "ms-transformation",
        "version": "1.0.0",
        "db_connected": db_connected,
        "timestamp": int(time.time()),
    }


@app.get("/")
def root():
    return {
        "message": "Transformation Service is running",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ══════════════════════════════════════════════════════════════════════
#  ENDPOINT PRINCIPAL — Transformación Avanzada (HU-20)
# ══════════════════════════════════════════════════════════════════════

@app.post(
    "/api/v1/transform/advanced",
    response_model=TransformResponse,
    summary="Ejecutar transformación avanzada",
    description=(
        "Aplica limpieza, detección de outliers (Winsorización) y "
        "normalización (Min-Max o Z-Score) sobre un dataset ingestado. "
        "El dataset debe existir y estar en estado VALID."
    ),
    tags=["transformation"],
)
def transform_advanced(
    body: TransformRequest,
    db: Session = Depends(get_db),
):
    """
    Endpoint POST que recibe:
      - dataset_load_id (str): ID del dataset cargado por ms-ingestion.
      - method (str): Método de normalización ('minmax' o 'zscore'). Default: 'minmax'.

    Retorna TransformResponse con el reporte estadístico en rules_applied.
    """
    run = process_advanced_transformation(
        db=db,
        dataset_load_id=body.dataset_load_id,
        method=body.method,
    )

    return TransformResponse(
        success=True,
        run_id=run.id,
        dataset_load_id=run.dataset_load_id,
        method=run.method,
        status=run.status,
        records_input=run.records_input,
        records_output=run.records_output,
        rules_applied=run.rules_applied,
        created_at=run.created_at,
    )
