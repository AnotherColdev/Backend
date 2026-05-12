from typing import Optional
from abc import ABC, abstractmethod

from fastapi import UploadFile

from app.models.dataset import DatasetLoad


class IIngestionService(ABC):
    @abstractmethod
    async def processUpload(
        self, 
        userId: str, 
        file: UploadFile, 
        sourceName: Optional[str] = None, 
        sourceType: Optional[str] = None
    ) -> DatasetLoad:
        pass
