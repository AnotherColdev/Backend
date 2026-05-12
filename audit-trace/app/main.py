from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.endpoints import audit
from app.core.middleware import TraceIdMiddleware
from app.core.exceptions import global_exception_handler
from sqlalchemy import text

with engine.connect() as con:
    con.execute(text("CREATE SCHEMA IF NOT EXISTS audit_trace"))
    con.commit()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audit Service")

app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(TraceIdMiddleware)

app.include_router(audit.router, prefix="", tags=["audit"])

@app.get("/health")
def health_check():
    import time
    try:
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False
        
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "service_name": "ms-audit-trace",
        "version": "1.0.0",
        "db_connected": db_connected,
        "timestamp": int(time.time())
    }