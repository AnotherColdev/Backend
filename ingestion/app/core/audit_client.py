import httpx
from app.core.config import settings
import logging

logger = logging.getLogger("IngestionAudit")

async def log_audit_action(action: str, details: str = None, user_id: str = None, trace_id: str = "Unknown"):
    payload = {
        "service_name": "ms-ingestion",
        "action": action,
        "user_id": user_id,
        "details": details
    }
    
    headers = {"X-Trace-Id": trace_id}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.MS_AUDIT_TRACE_URL}/",
                json=payload,
                headers=headers,
                timeout=5.0
            )
            if response.status_code != 201:
                logger.error(f"Error logging to audit-trace: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Fallo al conectar con ms-audit-trace: {str(e)}")
