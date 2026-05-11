from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from app.database import Base

class TranslationStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TransformationRun(Base):
    __tablename__ = "transformation_runs"

    id = Column(String, primary_key=True, index=True) # UUID string
    dataset_load_id = Column(String, index=True, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default=TranslationStatusEnum.IN_PROGRESS.value)
    rules_applied = Column(JSON, nullable=True)
    output_version = Column(String, default="1.0")
    
    transformed_data = relationship("TransformedZoneData", back_populates="run", cascade="all, delete-orphan")

class TransformedZoneData(Base):
    __tablename__ = "transformed_zone_data"

    id = Column(String, primary_key=True, index=True) # UUID string
    transformation_run_id = Column(String, ForeignKey("transformation_runs.id"), nullable=False, index=True)
    zone_code = Column(String, index=True, nullable=False)
    zone_name = Column(String, nullable=False)
    
    # Specific expected columns per requirements
    population_density = Column(Float, nullable=True)
    average_income = Column(Float, nullable=True)
    education_level = Column(Float, nullable=True)
    economic_activity_index = Column(Float, nullable=True)
    commercial_presence_index = Column(Float, nullable=True)
    
    other_variables_json = Column(JSON, nullable=True) # Catch-all for extra variables

    run = relationship("TransformationRun", back_populates="transformed_data")
