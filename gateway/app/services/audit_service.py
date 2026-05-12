"""
HU-28: Servicio de auditoría del BFF Gateway.
SRP: Solo se encarga de enviar eventos de traza a ms-audit-trace.
"""
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger("ExportAuditService")


async def sendExportAuditEvent(
    userId: str,
    executionId: str,
    exportType: str,
    exportFormat: str,
    zoneCode: Optional[str] = None,
    resultSummary: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Envía un evento de auditoría al ms-audit-trace tras una exportación exitosa.

    Args:
        userId: ID del usuario que ejecutó la exportación.
        executionId: ID de la ejecución de scoring asociada.
        exportType: Tipo de exportación ('RANKING_CSV' o 'ZONE_REPORT_JSON').
        exportFormat: Formato del archivo exportado ('csv' o 'json').
        zoneCode: Código de zona (solo para exportación de detalle).
        resultSummary: Resumen opcional de los datos exportados.

    Returns:
        True si el evento fue registrado correctamente, False en caso contrario.
    """
    tracePayload = {
        "dataset_load_id": executionId,
        "score_execution_id": executionId,
        "event_type": f"EXPORT_{exportType}",
        "status": "success",
        "user_id": userId,
        "parameters": {
            "export_format": exportFormat,
            "export_type": exportType,
            "zone_code": zoneCode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "result_summary": resultSummary or {},
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.MS_AUDIT_TRACE_URL}/api/v1/audit/trace",
                json=tracePayload,
            )
            if response.status_code in (200, 201):
                logger.info(
                    f"Audit event sent: {exportType} by user {userId} "
                    f"for execution {executionId}"
                )
                return True
            else:
                logger.warning(
                    f"Audit trace responded with status {response.status_code}: "
                    f"{response.text}"
                )
                return False
    except Exception as exc:
        logger.error(f"Failed to send audit event: {exc}")
        return False
