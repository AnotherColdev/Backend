from fastapi import Request
from fastapi.responses import JSONResponse
import traceback


class DomainException(Exception):
    """Excepción de dominio con mensaje y código de estado HTTP."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de excepciones para respuestas consistentes."""
    trace_id = getattr(request.state, "trace_id", "Unknown")

    if isinstance(exc, DomainException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.message,
                "trace_id": trace_id
            }
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal Server Error",
            "detail": str(exc),
            "trace_id": trace_id
        }
    )
