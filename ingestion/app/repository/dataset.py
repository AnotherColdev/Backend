from typing import Optional, List, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.exceptions import DomainException
from app.interfaces.datasetRepo import IDatasetRepository
from app.models.dataset import DatasetLoad, DatasetZone


class DatasetRepository(IDatasetRepository):
    def __init__(self, db: Session):
        self.db = db

    def getByHash(self, fileHash: str) -> Optional[DatasetLoad]:
        return (
            self.db.query(DatasetLoad)
            .filter(DatasetLoad.fileHash == fileHash)
            .first()
        )

    def getById(self, datasetId: str) -> Optional[DatasetLoad]:
        return (
            self.db.query(DatasetLoad)
            .filter(DatasetLoad.datasetId == datasetId)
            .first()
        )

    def getAll(self) -> List[DatasetLoad]:
        return (
            self.db.query(DatasetLoad)
            .order_by(desc(DatasetLoad.uploadedAt))
            .all()
        )

    def getZones(self, datasetId: Optional[str], search: Optional[str], limit: int, offset: int, department: Optional[str] = None) -> Tuple[List[DatasetZone], int]:
        query = self.db.query(DatasetZone)
        if datasetId:
            query = query.filter(DatasetZone.datasetId == datasetId)
        if department:
            query = query.filter(DatasetZone.department == department)
        else:
            # Heuristic: In Colombia, Municipalities have 5-digit codes. 
            # Departments have 2-digit codes. Filter for 5+ digits.
            query = query.filter(func.length(DatasetZone.zoneCode) >= 5)
        if search:
            query = query.filter(
                or_(
                    DatasetZone.zoneCode.ilike(f"%{search}%"),
                    DatasetZone.zoneName.ilike(f"%{search}%")
                )
            )

        total = query.count()
        zones = query.limit(limit).offset(offset).all()
        return zones, total

    def create(self, dataset: DatasetLoad, zones: List[DatasetZone] = None) -> DatasetLoad:
        try:
            self.db.add(dataset)
            if zones:
                self.db.add_all(zones)
            self.db.commit()
            self.db.refresh(dataset)
            return dataset
        except SQLAlchemyError as e:
            self.db.rollback()
            raise DomainException(
                f"Error de base de datos durante la persistencia: {str(e)}",
                status_code=500
            )
