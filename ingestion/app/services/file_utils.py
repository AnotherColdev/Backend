import hashlib
import io
import json
import os
import uuid

import pandas as pd
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import DomainException

ALLOWED_EXTENSIONS = {".csv", ".json"}
MAX_FILE_SIZE_MB   = 50
REQUIRED_COLUMNS   = ["zone_code", "zone_name"]
MAX_NULL_PERCENTAGE = 0.3


def validateExtension(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise DomainException(
            f"Extensión no permitida: '{ext}'. Solo se aceptan: {sorted(ALLOWED_EXTENSIONS)}",
            status_code=400
        )
    return ext


def generateUniqueFileName(ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


def hashContent(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def processValidation(df: pd.DataFrame) -> tuple[int, int, int, list]:
    cols = [str(c).lower().strip() for c in df.columns]
    df.columns = cols

    errors = []
    # 1. Check for required columns
    for requiredCol in REQUIRED_COLUMNS:
        if requiredCol not in cols:
            errors.append(f"El dataset no contiene la columna requerida: '{requiredCol}'")

    if errors:
        raise DomainException(" ".join(errors), status_code=400)

    # 2. Check for at least 3 numeric variables
    # We exclude REQUIRED_COLUMNS from numeric check
    potentialNumericCols = [c for c in cols if c not in REQUIRED_COLUMNS]
    numericDetected = []
    
    for col in potentialNumericCols:
        # Try to convert to numeric, if it fails, it's not a numeric variable for analysis
        original_values = df[col]
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if not df[col].isnull().all(): # If at least some values are numeric
            numericDetected.append(col)
        else:
            # If a column was expected to be numeric but isn't
            df[col] = original_values # restore

    if len(numericDetected) < 3:
        raise DomainException(
            f"El dataset debe contener al menos 3 variables numéricas. Se detectaron: {len(numericDetected)} ({', '.join(numericDetected)})",
            status_code=400
        )

    # 3. Check for null percentage in required columns
    for requiredCol in REQUIRED_COLUMNS:
        nullCount = df[requiredCol].isnull().sum()
        nullRatio = nullCount / len(df)
        if nullRatio > MAX_NULL_PERCENTAGE:
            raise DomainException(
                f"La columna '{requiredCol}' tiene {nullCount} nulos ({nullRatio:.1%}), superando el límite del 30%.",
                status_code=400
            )

    # 4. Detect duplicates (warning only as per HU-02)
    duplicatedCodes = df['zone_code'].duplicated(keep=False).sum()
    if duplicatedCodes > 0:
        # We don't raise error, just log or report in validation data
        pass

    validRecordCount = len(df.dropna(subset=REQUIRED_COLUMNS))
    invalidRecordCount = len(df) - validRecordCount

    # 5. Extract unique zones - Ensure zone_code is string
    # Try to find department column
    deptCol = next((c for c in cols if c in ["departamento", "department"]), None)
    
    uniqueZonesData = df.drop_duplicates(subset=['zone_code']).dropna(subset=['zone_code', 'zone_name'])
    zones = []
    for _, row in uniqueZonesData.iterrows():
        z_code = str(row['zone_code'])
        # If it was a float ending in .0, remove it
        if z_code.endswith('.0'):
            z_code = z_code[:-2]
        # Preserve leading zeros if it should be 2 digits (typical for DANE codes)
        if len(z_code) == 1 and z_code.isdigit():
            z_code = "0" + z_code
            
        zones.append({
            "zoneCode": z_code,
            "zoneName": str(row['zone_name']).strip(),
            "department": str(row[deptCol]).strip() if deptCol and pd.notnull(row[deptCol]) else None
        })

    return len(df), validRecordCount, invalidRecordCount, zones


def validateCsvContent(content: bytes) -> tuple[int, int, int, list]:
    try:
        df = pd.read_csv(io.BytesIO(content))
    except pd.errors.EmptyDataError:
        raise DomainException("El archivo CSV está vacío.", status_code=400)
    except Exception as e:
        raise DomainException(f"Error al parsear CSV: {str(e)}", status_code=400)

    return processValidation(df)


def validateJsonContent(content: bytes) -> tuple[int, int, int, list]:
    try:
        parsed = json.loads(content)
        df = pd.DataFrame(parsed)
    except json.JSONDecodeError as e:
        raise DomainException(f"El archivo JSON no es válido: {str(e)}", status_code=400)
    except Exception as e:
        raise DomainException(f"Error al procesar JSON a DataFrame: {str(e)}", status_code=400)

    if df.empty:
         raise DomainException("El archivo JSON está vacío o no contiene registros válidos.", status_code=400)

    return processValidation(df)


def saveToDisk(content: bytes, uniqueFileName: str) -> str:
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    filePath = os.path.join(settings.STORAGE_PATH, uniqueFileName)
    with open(filePath, "wb") as f:
        f.write(content)
    return filePath


async def validateAndProcessFile(file: UploadFile) -> tuple[str, str, int, dict]:
    content = await file.read()

    fileSizeBytes = len(content)
    if fileSizeBytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise DomainException(
            f"Archivo demasiado grande. Máximo permitido: {MAX_FILE_SIZE_MB} MB",
            status_code=400
        )

    ext = validateExtension(file.filename)
    fileHash = hashContent(content)

    if ext == ".csv":
        total, valid, invalid, zones = validateCsvContent(content)
    else:
        total, valid, invalid, zones = validateJsonContent(content)

    uniqueFileName = generateUniqueFileName(ext)
    saveToDisk(content, uniqueFileName)

    await file.seek(0)
    
    validationData = {
        "recordCount": total,
        "validRecordCount": valid,
        "invalidRecordCount": invalid,
        "zones": zones
    }

    return fileHash, uniqueFileName, fileSizeBytes, validationData
