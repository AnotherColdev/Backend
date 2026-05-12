from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

class DomainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

async def global_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", "Unknown")
    logger = getattr(request.state, "logger", None)
    
    if isinstance(exc, DomainException):
        if logger:
            logger.warning(f"Domain Error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.message,
                "trace_id": trace_id
            }
        )

    if logger:
        logger.error(f"Unhandled Exception: {str(exc)}\n{traceback.format_exc()}")
        
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal Server Error",
            "trace_id": trace_id
        }
    )
