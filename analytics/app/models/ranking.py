import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ScoreLevel(str, enum.Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"

class ZoneScore(Base):
    """
    Representa el score calculado de una zona.
    SRP: solo almacena datos de scoring, no tiene lógica.
    """
    __tablename__ = "zone_scores"
    __table_args__ = {"schema": "analytics"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String, nullable=False, index=True)
    zone_code = Column(String(50), nullable=False)
    zone_name = Column(String(255), nullable=False)
    score_value = Column(Float, nullable=False)
    score_level = Column(Enum(ScoreLevel), nullable=False)
    rank_position = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ScoreExecution(Base):
    """
    Representa una ejecución de scoring.
    SRP: solo almacena metadata de la ejecución.
    """
    __tablename__ = "score_executions"
    __table_args__ = {"schema": "analytics"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transformation_run_id = Column(String, nullable=False)
    configuration_id = Column(String, nullable=True)
    total_zones = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))