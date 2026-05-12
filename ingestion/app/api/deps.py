from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db
from app.interfaces.datasetRepo import IDatasetRepository
from app.interfaces.ingestionService import IIngestionService
from app.repository.dataset import DatasetRepository
from app.services.ingestion import IngestionService


def getDatasetRepository(db: Session = Depends(get_db)) -> IDatasetRepository:
    return DatasetRepository(db)


def getIngestionService(
    repo: IDatasetRepository = Depends(getDatasetRepository)
) -> IIngestionService:
    return IngestionService(repo)
