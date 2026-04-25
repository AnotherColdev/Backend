"""
Servicio de Transformación Avanzada — HU-20
============================================

Pipeline de procesamiento estadístico para datos territoriales.
Implementa limpieza, detección/tratamiento de outliers y normalización
con soporte para Min-Max y Z-Score.

Principios aplicados:
  - SRP: cada función tiene una única responsabilidad.
  - OCP: el pipeline es extensible (nuevos métodos de normalización).
  - DIP: recibe la sesión de BD como dependencia inyectada.
"""

import io
import os
import json
import uuid
import logging
from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainException
from app.models.models import TransformationRun, TransformedRecord

logger = logging.getLogger("TransformationService")


# ---------------------------------------------------------------------------
# 1. CARGA DE DATOS
# ---------------------------------------------------------------------------

def load_dataset_file(file_name: str) -> pd.DataFrame:
    """
    Lee un archivo CSV o JSON desde el storage compartido y devuelve un DataFrame.
    Soporta múltiples delimitadores para CSV.
    """
    file_path = os.path.join(settings.STORAGE_PATH, file_name)

    if not os.path.exists(file_path):
        raise DomainException(
            f"Archivo '{file_name}' no encontrado en storage ({file_path}).",
            status_code=404
        )

    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".csv":
        # Intentar con delimitador por defecto (coma), luego punto y coma
        try:
            df = pd.read_csv(file_path)
        except Exception:
            df = pd.read_csv(file_path, sep=";")
    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        df = pd.DataFrame(parsed)
    else:
        raise DomainException(
            f"Extensión '{ext}' no soportada. Solo CSV y JSON.",
            status_code=400
        )

    if df.empty:
        raise DomainException(
            "El archivo está vacío o no contiene registros.",
            status_code=400
        )

    # Normalizar nombres de columna
    df.columns = [str(c).lower().strip() for c in df.columns]
    return df


def get_dataset_load(db: Session, dataset_load_id: str) -> dict:
    """
    Consulta directa cross-schema a ingestion.dataset_loads.
    Retorna un dict con la metadata del dataset o None.
    """
    result = db.execute(
        text("""
            SELECT id, dataset_id, file_name, status, record_count
            FROM ingestion.dataset_loads
            WHERE dataset_id = :did
            LIMIT 1
        """),
        {"did": dataset_load_id}
    ).fetchone()

    if result is None:
        return None

    return {
        "id": result[0],
        "dataset_id": result[1],
        "file_name": result[2],
        "status": result[3],
        "record_count": result[4],
    }


# ---------------------------------------------------------------------------
# 2. LIMPIEZA (preservar lógica de HU-07)
# ---------------------------------------------------------------------------

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica el pipeline de limpieza:
      1. Convierte columnas potencialmente numéricas a float.
      2. Imputa valores nulos numéricos con la mediana de la columna.
      3. Elimina duplicados por zone_code (conserva el más reciente / último).
      4. Estandariza zone_name (title case, strip).
    """
    df = df.copy()

    # Detectar y convertir columnas numéricas
    non_key_cols = [c for c in df.columns if c not in ("zone_code", "zone_name")]
    for col in non_key_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Imputar nulos con mediana
    for col in numeric_cols:
        median_val = df[col].median()
        if pd.notna(median_val):
            df[col] = df[col].fillna(median_val)

    # Eliminar duplicados por zone_code (conservar el último = más reciente)
    if "zone_code" in df.columns:
        df = df.drop_duplicates(subset=["zone_code"], keep="last")

    # Estandarizar zone_name
    if "zone_name" in df.columns:
        df["zone_name"] = (
            df["zone_name"]
            .astype(str)
            .str.strip()
            .str.title()
        )

    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 3. TRATAMIENTO DE OUTLIERS
# ---------------------------------------------------------------------------

def detect_and_winsorize_outliers(
    df: pd.DataFrame,
    numeric_cols: List[str],
    z_threshold: float = 3.0,
    lower_percentile: float = 0.01,
    upper_percentile: float = 0.99,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Detecta outliers (valores fuera de ±z_threshold desviaciones estándar)
    y los capa al percentil inferior/superior (Winsorización).

    Retorna:
      - DataFrame con outliers capados.
      - Dict con el conteo de outliers por columna.
    """
    df = df.copy()
    outliers_count: Dict[str, int] = {}

    for col in numeric_cols:
        series = df[col]
        mean = series.mean()
        std = series.std()

        if std == 0 or pd.isna(std):
            outliers_count[col] = 0
            continue

        # Detectar outliers: |x - μ| > z_threshold * σ
        is_outlier = (series - mean).abs() > (z_threshold * std)
        count = int(is_outlier.sum())
        outliers_count[col] = count

        if count > 0:
            lower_bound = series.quantile(lower_percentile)
            upper_bound = series.quantile(upper_percentile)
            df[col] = series.clip(lower=lower_bound, upper=upper_bound)

    return df, outliers_count


# ---------------------------------------------------------------------------
# 4. NORMALIZACIÓN
# ---------------------------------------------------------------------------

def normalize_minmax(df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
    """
    Normalización Min-Max: (x - min) / (max - min)
    Produce valores estrictamente entre 0.0 y 1.0.
    Si max == min, el valor se establece en 0.0.
    """
    df = df.copy()
    for col in numeric_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max - col_min == 0:
            df[col] = 0.0
        else:
            df[col] = (df[col] - col_min) / (col_max - col_min)
    return df


def normalize_zscore(df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
    """
    Normalización Z-Score: (x - μ) / σ
    Produce valores con media ≈ 0 y desviación estándar ≈ 1.
    Si σ == 0, el valor se establece en 0.0.
    """
    df = df.copy()
    for col in numeric_cols:
        mean = df[col].mean()
        std = df[col].std()
        if std == 0 or pd.isna(std):
            df[col] = 0.0
        else:
            df[col] = (df[col] - mean) / std
    return df


# ---------------------------------------------------------------------------
# 5. GENERADOR DE REPORTE ESTADÍSTICO
# ---------------------------------------------------------------------------

def generate_stats_report(
    df: pd.DataFrame,
    numeric_cols: List[str],
    null_counts: Dict[str, int],
    outliers_counts: Dict[str, int],
) -> Dict[str, Any]:
    """
    Genera un diccionario con estadísticas descriptivas por cada variable numérica.
    Incluye: min, max, mean, std, null_count, outliers_count.
    """
    report: Dict[str, Any] = {}
    for col in numeric_cols:
        report[col] = {
            "min": round(float(df[col].min()), 6),
            "max": round(float(df[col].max()), 6),
            "mean": round(float(df[col].mean()), 6),
            "std": round(float(df[col].std()), 6),
            "null_count": null_counts.get(col, 0),
            "outliers_count": outliers_counts.get(col, 0),
        }
    return report


# ---------------------------------------------------------------------------
# 6. PIPELINE MAESTRO
# ---------------------------------------------------------------------------

def process_advanced_transformation(
    db: Session,
    dataset_load_id: str,
    method: str = "minmax",
) -> TransformationRun:
    """
    Pipeline maestro de transformación avanzada.

    Pasos:
      1. Validar que el dataset exista y esté en estado VALID.
      2. Cargar archivo desde storage.
      3. Limpieza (imputación mediana, dedup, estandarización).
      4. Conteo de nulos pre-limpieza (para reporte).
      5. Detección y Winsorización de outliers (±3σ → P1/P99).
      6. Normalización (Min-Max o Z-Score).
      7. Generación de reporte estadístico.
      8. Persistencia de run y registros normalizados.

    Args:
        db: Sesión SQLAlchemy.
        dataset_load_id: ID del dataset en ingestion.
        method: "minmax" o "zscore".

    Returns:
        TransformationRun con el resultado completo.
    """
    # ── Paso 1: Validar dataset ──
    dataset_info = get_dataset_load(db, dataset_load_id)
    if dataset_info is None:
        raise DomainException(
            f"Dataset con ID '{dataset_load_id}' no encontrado.",
            status_code=404
        )

    if dataset_info["status"] != "VALID":
        raise DomainException(
            f"El dataset '{dataset_load_id}' tiene estado '{dataset_info['status']}'. "
            f"Solo se pueden transformar datasets con estado 'VALID'.",
            status_code=400
        )

    # ── Paso 2: Cargar archivo ──
    file_name = dataset_info["file_name"]
    # El file_name en la BD es el nombre original, pero en disco se guardó
    # con un nombre UUID. Buscar archivos que coincidan o usar el nombre directo.
    # Revisando ingestion, el archivo se guarda con un UUID + extensión.
    # Necesitamos buscar en la BD el archivo guardado.
    # Solución: buscar en el storage por el dataset_id
    df_raw = _load_dataset_from_storage(db, dataset_load_id, file_name)
    records_input = len(df_raw)

    # ── Paso 3: Conteo de nulos pre-limpieza ──
    non_key_cols = [c for c in df_raw.columns if c not in ("zone_code", "zone_name")]
    for col in non_key_cols:
        df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
    numeric_cols = df_raw.select_dtypes(include=[np.number]).columns.tolist()
    null_counts = {col: int(df_raw[col].isnull().sum()) for col in numeric_cols}

    # ── Paso 4: Limpieza ──
    df_clean = clean_dataframe(df_raw)
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()

    # ── Paso 5: Winsorización de outliers ──
    df_winsorized, outliers_counts = detect_and_winsorize_outliers(
        df_clean, numeric_cols
    )

    # ── Paso 6: Normalización ──
    if method == "minmax":
        df_normalized = normalize_minmax(df_winsorized, numeric_cols)
    elif method == "zscore":
        df_normalized = normalize_zscore(df_winsorized, numeric_cols)
    else:
        raise DomainException(
            f"Método '{method}' no soportado. Use 'minmax' o 'zscore'.",
            status_code=400
        )

    records_output = len(df_normalized)

    # ── Paso 7: Reporte estadístico ──
    stats_report = generate_stats_report(
        df_normalized, numeric_cols, null_counts, outliers_counts
    )

    # Añadir metadatos al reporte
    report = {
        "method": method,
        "total_columns_processed": len(numeric_cols),
        "columns_processed": numeric_cols,
        "statistics": stats_report,
    }

    # ── Paso 8: Persistencia ──
    run = TransformationRun(
        id=str(uuid.uuid4()),
        dataset_load_id=dataset_load_id,
        method=method,
        status="COMPLETED",
        rules_applied=report,
        records_input=records_input,
        records_output=records_output,
    )

    # Crear registros transformados (formato "long" / melted)
    transformed_records = []
    for _, row in df_normalized.iterrows():
        zone_code = str(row.get("zone_code", ""))
        zone_name = str(row.get("zone_name", ""))
        for col in numeric_cols:
            # Buscar valor original en el df_winsorized (post-capado, pre-norm)
            original_val = df_winsorized.loc[
                df_winsorized["zone_code"].astype(str) == zone_code, col
            ]
            orig = float(original_val.iloc[0]) if len(original_val) > 0 else None

            transformed_records.append(TransformedRecord(
                id=str(uuid.uuid4()),
                run_id=run.id,
                zone_code=zone_code,
                zone_name=zone_name,
                column_name=col,
                original_value=orig,
                normalized_value=float(row[col]) if pd.notna(row[col]) else None,
            ))

    db.add(run)
    db.add_all(transformed_records)
    db.commit()
    db.refresh(run)

    logger.info(
        f"Transformación completada: run_id={run.id}, method={method}, "
        f"records_in={records_input}, records_out={records_output}"
    )

    return run


def _load_dataset_from_storage(
    db: Session, dataset_load_id: str, original_file_name: str
) -> pd.DataFrame:
    """
    Intenta cargar el archivo del dataset desde el storage.
    Busca todos los archivos en storage y trata de encontrar el correcto.
    Como ingestion guarda archivos con nombre UUID, listamos el directorio
    y buscamos por extensión y contenido si es necesario.
    """
    storage_path = settings.STORAGE_PATH

    if not os.path.exists(storage_path):
        raise DomainException(
            f"Directorio de storage '{storage_path}' no existe.",
            status_code=500
        )

    # Primero, intentar con el nombre original (por si se guardó así)
    original_path = os.path.join(storage_path, original_file_name)
    if os.path.exists(original_path):
        return load_dataset_file(original_file_name)

    # Si no, buscar todos los archivos en el storage y cargar el más reciente
    # que coincida con la extensión del archivo original
    ext = os.path.splitext(original_file_name)[1].lower()
    files = [
        f for f in os.listdir(storage_path)
        if f.endswith(ext) and os.path.isfile(os.path.join(storage_path, f))
    ]

    if not files:
        raise DomainException(
            f"No se encontraron archivos '{ext}' en el storage. "
            f"Archivo original: '{original_file_name}'.",
            status_code=404
        )

    # Ordenar por fecha de modificación (más reciente primero)
    files.sort(
        key=lambda f: os.path.getmtime(os.path.join(storage_path, f)),
        reverse=True
    )

    # Cargar el archivo más reciente
    return load_dataset_file(files[0])
