from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class TransformRequest(BaseModel):
    """
    Esquema de entrada para la transformación avanzada.
    - dataset_load_id: ID del dataset cargado en ingestion.
    - method: Método de normalización ('minmax' o 'zscore').
    """
    dataset_load_id: str
    method: str = "minmax"

    @field_validator("method")
    @classmethod
    def validate_method(cls, v):
        allowed = {"minmax", "zscore"}
        if v.lower() not in allowed:
            raise ValueError(
                f"Método '{v}' no válido. Métodos permitidos: {sorted(allowed)}"
            )
        return v.lower()


class ColumnStats(BaseModel):
    """Estadísticas descriptivas de una columna procesada."""
    column: str
    min: float
    max: float
    mean: float
    std: float
    null_count: int
    outliers_count: int


class TransformResponse(BaseModel):
    """
    Respuesta de la transformación avanzada.
    Incluye metadata de la ejecución y el reporte estadístico en rules_applied.
    """
    success: bool
    run_id: str
    dataset_load_id: str
    method: str
    status: str
    records_input: int
    records_output: int
    rules_applied: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class TransformListResponse(BaseModel):
    """Respuesta para listar transformaciones."""
    success: bool
    total: int
    data: List[TransformResponse]


class ErrorResponse(BaseModel):
    """Respuesta de error estándar."""
    error: bool = True
    message: str
    trace_id: Optional[str] = None
