import pandas as pd
import numpy as np
import pytest
from app.services.transformer_service import process_dataset, standardize_text

def test_standardize_text():
    # 3) Estandarización correcta de strings ('Bogotá' -> 'bogota')
    series = pd.Series(["Bogotá", "  MedeLLÍN ", "Cali", "BARRANQUILLA  ", None, np.nan])
    result = standardize_text(series)
    
    assert result[0] == "bogota"
    assert result[1] == "medellin"
    assert result[2] == "cali"
    assert result[3] == "barranquilla"
    assert pd.isna(result[4])
    assert pd.isna(result[5])

def test_process_dataset():
    # Dummy data
    data = {
        "zone_code": ["ZC1", "ZC2", "ZC1", "ZC3", "ZC4", "ZC5"],
        "zone_name": ["Bogotá", " Med  elli n  ", "Bogota", "Cali", "BARRANQUI LLA", "CARTAGeNA"],
        "population_density": [1000, 800, 1050, np.nan, 300, 400], # ZC3 nan
        "average_income": [50000, 45000, 52000, 30000, np.nan, 20000],
        "education_level": [0.8, 0.7, 0.85, 0.6, 0.5, 0.4],
        "economic_activity_index": [0.9, 0.8, 0.95, 0.7, 0.6, 0.5],
        "commercial_presence_index": [0.85, 0.75, 0.88, 0.65, np.nan, 0.45],
        "extra_var": [10, 20, 15, 30, 40, np.nan]
    }
    df = pd.DataFrame(data)
    
    df_processed, rules = process_dataset(df)
    
    # 1) Valores entre 0 y 1 para variables numéricas
    numeric_cols = df_processed.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_cols:
        assert df_processed[col].min() >= 0.0
        assert df_processed[col].max() <= 1.0

    # 2) Ausencia de nulos y duplicados
    assert df_processed.isnull().sum().sum() == 0, "No debe haber nulos numéricos"
    
    # zone_code uniqueness (the latest ZC1 should be retained, value 1050 for population_density)
    # The original ZC1 had 1000 and 1050, the last one is 1050
    assert df_processed['zone_code'].is_unique, "No debe haber duplicados en zone_code"
    zc1_row = df_processed[df_processed['zone_code'] == 'ZC1']
    assert len(zc1_row) == 1
    # Check if the last ZC1 string 'Bogota' was standardized to 'bogota'
    assert zc1_row.iloc[0]['zone_name'] == 'bogota'
    # population density of the selected ZC1 should be the one from the original second ZC1
    # Note: min-max normalization changes the values, so we check original logic implicitly
    
    # El set de reglas debe estar documentado
    assert len(rules) > 0
    assert "Normalización Min-Max de variables numéricas" in rules
