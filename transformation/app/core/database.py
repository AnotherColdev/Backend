from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Generador de sesión de BD para inyección de dependencias."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Crea el schema 'transformation' si no existe y sincroniza las tablas.
    Se ejecuta al iniciar la aplicación.
    """
    from app.models.models import Base as ModelBase
    with engine.connect() as con:
        con.execute(text("CREATE SCHEMA IF NOT EXISTS transformation"))
        con.commit()
    ModelBase.metadata.create_all(bind=engine)
