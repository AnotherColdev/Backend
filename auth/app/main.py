from fastapi import FastAPI, Depends
from app.core.database import engine, Base, get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.endpoints import auth, users, health
from app.models.user import User, UserRole
from app.core.security import getPasswordHash
import time

# Create schema if not exists
with engine.connect() as con:
    con.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
    con.commit()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auth Service")

@app.on_event("startup")
def createInitialData():
    # Manually ensure username column exists for existing tables
    try:
        with engine.connect() as con:
            con.execute(text("ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS username VARCHAR UNIQUE"))
            con.commit()
    except Exception:
        pass # It might already exist or schema not yet ready
        
    db = next(get_db())
    adminExists = db.query(User).filter(User.email == "admin@territorial.com").first()
    if not adminExists:
        adminUser = User(
            email="admin@territorial.com",
            username="admin",
            password_hash=getPasswordHash("admin123"),
            full_name="System Admin",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(adminUser)
        db.commit()

app.include_router(auth.router, tags=["auth"])
app.include_router(users.router, prefix="/admin/users", tags=["admin"])
app.include_router(health.router)


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
        "service_name": "ms-auth",
        "version": "1.0.0",
        "db_connected": dbConnected,
        "timestamp": int(time.time())
    }
