from sqlalchemy import Column, Integer, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class DatasetLoad(Base):
    __tablename__ = "dataset_loads"
    __table_args__ = {'schema': 'ingestion'}

    id                 = Column(Integer, primary_key=True, index=True)
    datasetId          = Column("dataset_id", String, unique=True, index=True)
    userId             = Column("user_id",    String, index=True)
    fileName           = Column("file_name",  String)
    sourceName         = Column("source_name", String, nullable=True)
    sourceType         = Column("source_type", String, nullable=True)
    fileHash           = Column("file_hash",  String, unique=True, index=True)
    fileSize           = Column("file_size",  BigInteger)
    recordCount        = Column("record_count", Integer, default=0)
    validRecordCount   = Column("valid_record_count", Integer, default=0)
    invalidRecordCount = Column("invalid_record_count", Integer, default=0)
    uploadedAt         = Column("uploaded_at", DateTime, default=datetime.utcnow)
    status             = Column(String, default="UPLOADED")

    zones = relationship("DatasetZone", back_populates="datasetLoad", cascade="all, delete-orphan")


class DatasetZone(Base):
    __tablename__ = "dataset_zones"
    __table_args__ = {'schema': 'ingestion'}

    id          = Column(Integer, primary_key=True, index=True)
    datasetId   = Column("dataset_id", String, ForeignKey("ingestion.dataset_loads.dataset_id"), index=True)
    zoneCode    = Column("zone_code", String, index=True)
    zoneName    = Column("zone_name", String)
    department  = Column(String, index=True, nullable=True)

    datasetLoad = relationship("DatasetLoad", back_populates="zones")
