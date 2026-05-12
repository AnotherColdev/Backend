import uuid
from typing import Optional

from fastapi import UploadFile

from app.interfaces.datasetRepo import IDatasetRepository
from app.interfaces.ingestionService import IIngestionService
from app.models.dataset import DatasetLoad, DatasetZone
from app.services.file_utils import validateAndProcessFile
from app.core.exceptions import DomainException


class IngestionService(IIngestionService):
    def __init__(self, datasetRepo: IDatasetRepository):
        self.datasetRepo = datasetRepo

    async def processUpload(
        self, 
        userId: str, 
        file: UploadFile, 
        sourceName: Optional[str] = None, 
        sourceType: Optional[str] = None
    ) -> DatasetLoad:
        fileHash, uniqueFileName, fileSizeBytes, valData = await validateAndProcessFile(file)

        existingDataset = self.datasetRepo.getByHash(fileHash)
        if existingDataset:
            raise DomainException(
                message=(
                    f"Ya existe un dataset con contenido idéntico "
                    f"(hash: {fileHash}) registrado como '{existingDataset.fileName}'."
                ),
                status_code=409
            )

        newDataset = DatasetLoad(
            datasetId          = uuid.uuid4().hex,
            userId             = userId,
            fileName           = file.filename,
            fileHash           = fileHash,
            fileSize           = fileSizeBytes,
            recordCount        = valData["recordCount"],
            validRecordCount   = valData["validRecordCount"],
            invalidRecordCount = valData["invalidRecordCount"],
            sourceName         = sourceName,
            sourceType         = sourceType,
            status             = "VALID"
        )
        
        zones = [
            DatasetZone(
                zoneCode=z["zoneCode"],
                zoneName=z["zoneName"],
                department=z.get("department"),
                datasetLoad=newDataset
            )
            for z in valData["zones"]
        ]

        return self.datasetRepo.create(newDataset, zones)
