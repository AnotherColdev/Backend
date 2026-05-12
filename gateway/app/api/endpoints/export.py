"""
HU-28: Endpoints de exportación del BFF Gateway.
Implementa los endpoints de exportación de ranking (CSV) y detalle de zona (JSON).

Actividades técnicas:
  1. GET /api/v1/export/ranking?execution_id=xxx&format=csv → CSV con ranking
  2. GET /api/v1/export/zone-report/{zone_code}?format=json → JSON de zona
  3. Validación de estado COMPLETED antes de exportar
  4. Registro de evento de auditoría tras exportación exitosa
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse

from app.services.export_service import (
    fetchRankingData,
    generateRankingCsv,
    buildZoneReport,
    validateExecutionStatus,
)
from app.services.audit_service import sendExportAuditEvent

logger = logging.getLogger("ExportEndpoints")

router = APIRouter(prefix="/export", tags=["Exportación HU-28"])


def _getUserId(request: Request) -> str:
    """Extrae el user_id del JWT decodificado en el middleware de autenticación."""
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        return user.get("sub", user.get("user_id", "anonymous"))
    return "anonymous"


@router.get(
    "/ranking",
    summary="Exportar ranking de zonas en CSV",
    description=(
        "Genera y descarga un archivo CSV con el ranking completo de zonas "
        "para una ejecución de scoring dada. Encabezados: Zona, Indicadores, "
        "Score, Nivel, Recomendación. Codificación UTF-8 con BOM para Excel."
    ),
    responses={
        200: {
            "description": "Archivo CSV descargado exitosamente",
            "content": {"text/csv": {}},
        },
        400: {"description": "Parámetros inválidos"},
        403: {"description": "Ejecución no completada"},
        502: {"description": "Error de comunicación con ms-analytics"},
    },
)
async def exportRanking(
    request: Request,
    backgroundTasks: BackgroundTasks,
    execution_id: str = Query(
        ...,
        description="ID de la ejecución de scoring a exportar",
        min_length=1,
    ),
    format: str = Query(
        "csv",
        description="Formato de exportación (solo 'csv' soportado)",
    ),
):
    """
    HU-28 — Endpoint de Ranking (CSV).
    1. Valida que la ejecución esté COMPLETED.
    2. Obtiene datos de ranking de ms-analytics.
    3. Genera CSV en memoria con StreamingResponse.
    4. Registra evento de auditoría en background.
    """
    # --- Validación de formato ---
    if format.lower() != "csv":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FORMAT",
                "message": (
                    f"Formato '{format}' no soportado para ranking. "
                    "Use format=csv."
                ),
            },
        )

    # --- Validación de estado COMPLETED ---
    validation = await validateExecutionStatus(execution_id)
    if not validation["valid"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "EXPORT_NOT_ALLOWED",
                "status": validation["status"],
                "message": validation["message"],
            },
        )

    # --- Obtener datos de ranking ---
    try:
        rankingData = await fetchRankingData(execution_id)
    except Exception as exc:
        logger.error(f"Error fetching ranking data: {exc}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "UPSTREAM_ERROR",
                "message": (
                    "Error al obtener datos de ranking desde el servicio de "
                    f"analítica: {str(exc)}"
                ),
            },
        )

    # --- Generar CSV ---
    csvBytes = generateRankingCsv(rankingData)
    totalZones = len(rankingData.get("zones", []))

    # --- Nombre del archivo ---
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"ranking_{execution_id[:8]}_{timestamp}.csv"

    # --- Auditoría en background ---
    userId = _getUserId(request)
    backgroundTasks.add_task(
        sendExportAuditEvent,
        userId=userId,
        executionId=execution_id,
        exportType="RANKING_CSV",
        exportFormat="csv",
        resultSummary={
            "total_zones": totalZones,
            "filename": filename,
        },
    )

    logger.info(
        f"CSV export generated: {filename} ({totalZones} zones) "
        f"by user {userId}"
    )

    # --- StreamingResponse ---
    return StreamingResponse(
        iter([csvBytes]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(csvBytes)),
            "X-Export-Total-Zones": str(totalZones),
            "X-Export-Execution-Id": execution_id,
            "Access-Control-Expose-Headers": (
                "Content-Disposition, X-Export-Total-Zones, X-Export-Execution-Id"
            ),
        },
    )


@router.get(
    "/zone-report/{zone_code}",
    summary="Exportar reporte completo de zona en JSON",
    description=(
        "Retorna el reporte completo de una zona incluyendo indicadores, "
        "scores, predicción, combined_score y recomendación."
    ),
    responses={
        200: {"description": "Reporte JSON de la zona"},
        400: {"description": "Parámetros inválidos"},
        404: {"description": "Zona no encontrada"},
    },
)
async def exportZoneReport(
    zone_code: str,
    request: Request,
    backgroundTasks: BackgroundTasks,
    format: str = Query(
        "json",
        description="Formato de exportación (solo 'json' soportado)",
    ),
):
    """
    HU-28 — Endpoint de Detalle (JSON).
    1. Obtiene datos consolidados de la zona desde ms-analytics.
    2. Enriquece con predicción y recomendación.
    3. Registra evento de auditoría en background.
    """
    # --- Validación de formato ---
    if format.lower() != "json":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FORMAT",
                "message": (
                    f"Formato '{format}' no soportado para reporte de zona. "
                    "Use format=json."
                ),
            },
        )

    # --- Validación del zone_code ---
    if not zone_code or len(zone_code.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_ZONE_CODE",
                "message": "El código de zona no puede estar vacío.",
            },
        )

    # --- Construir reporte ---
    try:
        report = await buildZoneReport(zone_code.strip())
    except Exception as exc:
        logger.error(f"Error building zone report for {zone_code}: {exc}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "UPSTREAM_ERROR",
                "message": (
                    "Error al construir el reporte de zona desde el servicio "
                    f"de analítica: {str(exc)}"
                ),
            },
        )

    # --- Auditoría en background ---
    userId = _getUserId(request)
    backgroundTasks.add_task(
        sendExportAuditEvent,
        userId=userId,
        executionId=report.get("score", {}).get("score_value", "N/A"),
        exportType="ZONE_REPORT_JSON",
        exportFormat="json",
        zoneCode=zone_code,
        resultSummary={
            "zone_code": zone_code,
            "score_level": report.get("score", {}).get("score_level", "N/A"),
        },
    )

    logger.info(
        f"Zone report exported: {zone_code} by user {userId}"
    )

    return JSONResponse(
        content=report,
        headers={
            "X-Export-Zone-Code": zone_code,
            "Access-Control-Expose-Headers": "X-Export-Zone-Code",
        },
    )
