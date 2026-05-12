import httpx
import os
import asyncio

AUDIT_TRACE_URL = os.getenv("AUDIT_TRACE_URL", "http://audit-trace:8000")

async def send_trace_event(event_data: dict):
    """Envía evento de trazabilidad a ms-audit-trace - HU-19"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUDIT_TRACE_URL}/api/v1/audit/trace",
                json=event_data
            )
            return response.status_code == 200
    except Exception as e:
        print(f"⚠️ Error enviando a audit-trace: {e}")
        return False