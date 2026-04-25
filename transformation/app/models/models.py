import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class TransformationRun(Base):
    """
    Representa una ejecución de transformación sobre un dataset.
    Almacena metadata, método utilizado y reporte estadístico.
    SRP: solo almacena datos de la ejecución, no tiene lógica.
    """
    __tablename__ = "transformation_runs"
    __table_args__ = {"schema": "transformation"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_load_id = Column(String, nullable=False, index=True)
    method = Column(String(10), nullable=False)  # "minmax" o "zscore"
    status = Column(String(20), nullable=False, default="PROCESSING")
    rules_applied = Column(JSON, nullable=True)  # Reporte estadístico por columna
    records_input = Column(Integer, default=0)
    records_output = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    records = relationship(
        "TransformedRecord",
        back_populates="run",
        cascade="all, delete-orphan"
    )


class TransformedRecord(Base):
    """
    Registro individual normalizado.
    Cada fila representa un valor normalizado de una columna para una zona.
    SRP: solo almacena un dato transformado.
    """
    __tablename__ = "transformed_records"
    __table_args__ = {"schema": "transformation"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(
        String,
        ForeignKey("transformation.transformation_runs.id"),
        nullable=False,
        index=True
    )
    zone_code = Column(String(50), nullable=False)
    zone_name = Column(String(255), nullable=False)
    column_name = Column(String(100), nullable=False)
    original_value = Column(Float, nullable=True)
    normalized_value = Column(Float, nullable=True)

    run = relationship("TransformationRun", back_populates="records")
