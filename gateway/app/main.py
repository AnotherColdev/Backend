from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from app.api.endpoints import proxy
from app.api.endpoints.export import router as export_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.auth_middleware import auth_middleware
import uuid
import logging

logger = logging.getLogger("GatewayService")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [Trace: %(trace_id)s] - %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

app = FastAPI(title="BFF API Gateway")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    
    adapter = logging.LoggerAdapter(logger, {'trace_id': trace_id})
    request.state.logger = adapter
    
    if request.url.path.endswith("/health"):
        adapter.info(f"Health check request received for {request.url.path}")
    else:
        adapter.info(f"Gateway proxying request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        if not request.url.path.endswith("/health"):
            adapter.info(f"Gateway response status: {response.status_code}")
        return response
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail, "trace_id": trace_id})
    except Exception as e:
        adapter.error(f"Gateway Internal Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Gateway Error", "trace_id": trace_id})

# Auth Middleware (must be after CORS but effectively wraps other controllers)
@app.middleware("http")
async def wrap_auth_middleware(request: Request, call_next):
    return await auth_middleware(request, call_next)

# Add CORS last so it is the OUTERMOST middleware (called first for requests).
# In FastAPI/Starlette, middlewares are executed in reverse order of addition.
# Current Stack: CORSMiddleware -> wrap_auth_middleware -> add_process_time_header -> Router
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://[::1]:5173",
        "http://[::1]:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy.router, prefix="/api/v1", tags=["proxy"])
app.include_router(export_router, prefix="/api/v1", tags=["export"])

@app.get("/health")
def health_check():
    import time
    return {
        "status": "healthy",
        "service_name": "bff-gateway",
        "version": "1.0.0",
        "db_connected": False,
        "timestamp": int(time.time())
    }
