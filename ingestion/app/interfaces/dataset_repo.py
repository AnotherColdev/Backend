from abc import ABC, abstractmethod
from typing import Optional
from app.models.dataset import DatasetLoad

class IDatasetRepository(ABC):
    @abstractmethod
    def get_by_hash(self, file_hash: str) -> Optional[DatasetLoad]:
        pass

    @abstractmethod
    def create(self, dataset: DatasetLoad) -> DatasetLoad:
        pass
