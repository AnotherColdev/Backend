from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from sqlalchemy import text
    from app.models.ranking import Base
    with engine.connect() as con:
        con.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
        con.commit()
    Base.metadata.create_all(bind=engine)