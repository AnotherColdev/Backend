from fastapi import FastAPI
from app.core.database import engine, Base
from app.api.endpoints import dataset
from app.api.endpoints.zones import router as zonesRouter
from app.api.endpoints.health import router as healthRouter
from app.core.middleware import TraceIdMiddleware
from app.core.exceptions import global_exception_handler
from sqlalchemy import text
import time

with engine.connect() as con:
    con.execute(text("CREATE SCHEMA IF NOT EXISTS ingestion"))
    con.commit()

with engine.connect() as con:
    # Add department column if it doesn't exist
    try:
        con.execute(text("ALTER TABLE ingestion.dataset_zones ADD COLUMN IF NOT EXISTS department VARCHAR"))
        con.commit()
    except Exception:
        # Table might not exist yet, create_all will handle it
        pass

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ingestion Service",
    description="Microservicio de ingesta de datos territoriales",
    version="1.0.0",
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_middleware(TraceIdMiddleware)

# Routes
app.include_router(dataset.router, prefix="/datasets", tags=["datasets"])
app.include_router(zonesRouter)
app.include_router(healthRouter)

@app.get("/")
def root():
    return {"message": "Ingestion Service is running", "version": "1.0.0"}

@app.get("/health-check")
def healthCheck():
    try:
        with engine.connect() as con:
            con.execute(text("SELECT 1"))
        dbConnected = True
    except Exception:
        dbConnected = False
        
    return {
        "status": "healthy" if dbConnected else "unhealthy",
        "service_name": "ms-ingestion",
        "version": "1.0.0",
        "db_connected": dbConnected,
        "timestamp": int(time.time())
    }
