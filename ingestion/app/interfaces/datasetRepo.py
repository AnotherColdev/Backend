from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from app.models.dataset import DatasetLoad, DatasetZone


class IDatasetRepository(ABC):
    @abstractmethod
    def getByHash(self, fileHash: str) -> Optional[DatasetLoad]:
        pass

    @abstractmethod
    def getById(self, datasetId: str) -> Optional[DatasetLoad]:
        pass

    @abstractmethod
    def getAll(self) -> List[DatasetLoad]:
        pass

    @abstractmethod
    def getZones(self, datasetId: Optional[str], search: Optional[str], limit: int, offset: int, department: Optional[str] = None) -> Tuple[List[DatasetZone], int]:
        pass

    @abstractmethod
    def create(self, dataset: DatasetLoad, zones: List[DatasetZone] = None) -> DatasetLoad:
        pass
