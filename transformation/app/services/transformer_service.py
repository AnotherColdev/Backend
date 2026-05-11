import pandas as pd
import numpy as np
from unidecode import unidecode
from typing import Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.transformation import TransformationRun, TransformedZoneData, TranslationStatusEnum
import uuid
from datetime import datetime, timezone

def standardize_text(text: pd.Series) -> pd.Series:
    """Estandarizar textos: quitar tildes, convertir a minúsculas, eliminar espacios extra."""
    def clean_val(x):
        if pd.isna(x) or str(x).lower() in ['nan', 'none']:
            return np.nan
        # Remueve tildes, minúsculas y elimina absolutamente todos los espacios
        return unidecode(str(x)).lower().replace(' ', '')
    
    return text.apply(clean_val)

def process_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    rules_applied = []
    
    # Eliminar duplicados por zone_code conservando el más reciente (last)
    rules_applied.append("Eliminar duplicados por zone_code (keep='last')")
    df = df.drop_duplicates(subset=['zone_code'], keep='last').copy()
    
    # Estandarizar textos en zone_name
    if 'zone_name' in df.columns:
        df['zone_name'] = standardize_text(df['zone_name'])
        rules_applied.append("Estandarizar texto en zone_name")
        
    if 'zone_code' in df.columns:
        df['zone_code'] = df['zone_code'].astype(str).str.strip()

    # Identificar numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Imputar nulos con mediana
    for col in numeric_cols:
        if df[col].isnull().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
    rules_applied.append("Imputar nulos numéricos con mediana")
    
    # Normalización Min-Max [0, 1]
    for col in numeric_cols:
        min_val = df[col].min()
        max_val = df[col].max()
        if max_val > min_val:
            df[col] = (df[col] - min_val) / (max_val - min_val)
        else:
            df[col] = 0.0
    rules_applied.append("Normalización Min-Max de variables numéricas")

    return df, rules_applied

class TransformerService:
    def __init__(self, db: Session):
        self.db = db

    async def fetch_mock_dataset(self, dataset_load_id: str) -> pd.DataFrame:
        """
        Simula la descarga de datos desde ms-ingestion.
        """
        if dataset_load_id == "INVALID":
            raise ValueError("Dataset not found or not in VALID state")
        
        # Dummy DataFrame
        data = {
            "zone_code": ["ZC1", "ZC2", "ZC1", "ZC3", "ZC4", "ZC5"],
            "zone_name": ["Bogotá", " Medellin  ", "Bogota", "Cali", "BARRANQUILLA", "CARTAGENA"],
            "population_density": [1000, 800, 1050, np.nan, 300, 400], # ZC3 nan
            "average_income": [50000, 45000, 52000, 30000, np.nan, 20000],
            "education_level": [0.8, 0.7, 0.85, 0.6, 0.5, 0.4],
            "economic_activity_index": [0.9, 0.8, 0.95, 0.7, 0.6, 0.5],
            "commercial_presence_index": [0.85, 0.75, 0.88, 0.65, np.nan, 0.45],
            "extra_var": [10, 20, 15, 30, 40, np.nan]
        }
        return pd.DataFrame(data)

    async def transform(self, dataset_load_id: str) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        run = TransformationRun(
            id=run_id,
            dataset_load_id=dataset_load_id,
            status=TranslationStatusEnum.IN_PROGRESS.value
        )
        self.db.add(run)
        self.db.commit()
        
        try:
            # Obtener datos (Mock)
            df = await self.fetch_mock_dataset(dataset_load_id)
            
            # Procesar datos
            df_processed, rules = process_dataset(df)
            
            # Guardar datos transformados
            records = []
            standard_cols = {"population_density", "average_income", "education_level", 
                             "economic_activity_index", "commercial_presence_index"}
            
            for _, row in df_processed.iterrows():
                row_dict = row.to_dict()
                other_vars = {}
                for k, v in row_dict.items():
                    if k not in standard_cols and k not in ["zone_code", "zone_name"]:
                        other_vars[k] = v if pd.notna(v) else None
                
                tzd = TransformedZoneData(
                    id=str(uuid.uuid4()),
                    transformation_run_id=run_id,
                    zone_code=row_dict["zone_code"],
                    zone_name=row_dict["zone_name"],
                    population_density=row_dict.get("population_density"),
                    average_income=row_dict.get("average_income"),
                    education_level=row_dict.get("education_level"),
                    economic_activity_index=row_dict.get("economic_activity_index"),
                    commercial_presence_index=row_dict.get("commercial_presence_index"),
                    other_variables_json=other_vars
                )
                records.append(tzd)
            
            self.db.bulk_save_objects(records)
            
            run.status = TranslationStatusEnum.COMPLETED.value
            run.finished_at = datetime.now(timezone.utc)
            run.rules_applied = rules
            self.db.commit()
            
            return {
                "transformation_run_id": run_id,
                "total_zones_processed": len(records),
                "rules_applied": rules,
                "output_version": run.output_version
            }
            
        except ValueError as e:
            run.status = TranslationStatusEnum.FAILED.value
            run.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            raise e
        except Exception as e:
            run.status = TranslationStatusEnum.FAILED.value
            run.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            raise Exception("Transformation failed") from e
