from abc import ABC, abstractmethod
from fastapi import UploadFile
from app.models.dataset import DatasetLoad

class IIngestionService(ABC):
    @abstractmethod
    async def process_upload(self, user_id: str, file: UploadFile) -> DatasetLoad:
        pass
