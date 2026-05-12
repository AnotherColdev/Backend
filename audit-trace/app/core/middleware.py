import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ConfigurationService")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [Trace: %(trace_id)s] - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        adapter = logging.LoggerAdapter(logger, {'trace_id': trace_id})
        request.state.logger = adapter
        
        adapter.info(f"Received request: {request.method} {request.url.path}")
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        adapter.info(f"Response status: {response.status_code}")
        return response
