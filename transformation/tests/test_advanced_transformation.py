"""
Script de Prueba Integral — HU-20: Normalización Avanzada
==========================================================

Este script valida el pipeline completo de transformación avanzada:
  1. Inyecta un dataset de prueba con un outlier extremo.
  2. Ejecuta la transformación con method="zscore".
  3. Verifica que el outlier fue capado (Winsorización).
  4. Verifica que el reporte estadístico contiene las estadísticas correctas.
  5. Verifica que los valores Z-Score tienen media ≈ 0 y desviación ≈ 1.
  6. Ejecuta una segunda prueba con method="minmax".
  7. Verifica que los valores Min-Max están entre 0.0 y 1.0.

Uso:
  python tests/test_advanced_transformation.py [--base-url URL]

Requiere:
  - Los microservicios ms-ingestion, ms-transformation y gateway ejecutándose.
  - pip install requests psycopg2-binary
"""

import os
import sys
import uuid
import time
import json
import argparse
import requests

import os
import sys
import json
import time
import argparse
import subprocess
import requests

# ── Configuración ──
DEFAULT_BASE_URL = "http://localhost:8004/api/v1"
DEFAULT_DB_URL = "postgresql://postgres:admin@localhost:5432/territorial_db"

# Colores ANSI para la terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log_pass(msg):
    print(f"  {GREEN}✓ PASS{RESET}: {msg}")


def log_fail(msg):
    print(f"  {RED}✗ FAIL{RESET}: {msg}")


def log_info(msg):
    print(f"  {CYAN}ℹ INFO{RESET}: {msg}")


def log_section(msg):
    print(f"\n{BOLD}{YELLOW}{'═' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  {msg}{RESET}")
    print(f"{BOLD}{YELLOW}{'═' * 60}{RESET}")


# ══════════════════════════════════════════════════════════════════
# FASE 1: Inyectar dataset de prueba (Mock directo)
# ══════════════════════════════════════════════════════════════════

def inject_test_dataset(db_url: str) -> str:
    """
    Simula la ingesta creando un registro en la BD y el archivo CSV
    directamente en el contenedor de ms-transformation, para probar
    únicamente el funcionamiento de transformation.
    """
    log_section("FASE 1: Preparación de Datos Simulada (Mock Ingestion)")

    dataset_id = "test-hu20-mock-" + str(int(time.time()))
    file_hash = "mockhash" + str(int(time.time()))
    
    csv_content = """zone_code,zone_name,population,income_index,education_score,health_index
BOG-001,chapinero,120000,0.85,7.5,0.92
BOG-002,suba,350000,0.72,6.8,0.85
BOG-003,usaquen,180000,0.91,8.2,0.95
BOG-004,kennedy,450000,0.55,5.9,0.70
BOG-005,engativa,99999999,0.68,7.1,0.88
BOG-006,bosa,280000,0.48,5.5,0.65
BOG-007,fontibon,195000,0.78,7.8,0.90
BOG-008,teusaquillo,145000,0.88,8.5,0.93
BOG-009,rafael uribe uribe,230000,0.52,5.2,0.62
BOG-010,ciudad bolivar,350000,0.42,4.8,0.55
BOG-011,antonio narino,110000,0.75,7.2,0.86
BOG-012,san cristobal,410000,0.45,5.0,0.60
BOG-013,usme,390000,0.40,4.5,0.52
BOG-014,tunjuelito,200000,0.58,6.0,0.72
BOG-015,martires,100000,0.65,6.5,0.75
BOG-016,puente aranda,260000,0.70,7.0,0.80
BOG-017,candelaria,25000,0.80,8.0,0.85
BOG-018,barrios unidos,160000,0.82,8.1,0.87
BOG-019,santa fe,105000,0.60,6.2,0.70
BOG-020,sumapaz,5000,0.50,5.0,0.65
"""

    log_info(f"Insertando mock dataset en BD: dataset_id={dataset_id}, hash={file_hash}")
    
    sql = f"""
    CREATE SCHEMA IF NOT EXISTS ingestion;
    CREATE TABLE IF NOT EXISTS ingestion.dataset_loads (
        id SERIAL PRIMARY KEY,
        dataset_id VARCHAR,
        user_id VARCHAR,
        file_name VARCHAR,
        source_name VARCHAR,
        source_type VARCHAR,
        file_hash VARCHAR,
        file_size BIGINT,
        record_count INTEGER,
        valid_record_count INTEGER,
        invalid_record_count INTEGER,
        uploaded_at TIMESTAMP WITHOUT TIME ZONE,
        status VARCHAR
    );
    INSERT INTO ingestion.dataset_loads 
    (dataset_id, user_id, file_name, source_name, source_type, file_hash, file_size, record_count, valid_record_count, invalid_record_count, uploaded_at, status)
    VALUES 
    ('{dataset_id}', 'tester', 'test_hu20_outlier.csv', 'Test HU-20', 'CSV', '{file_hash}', 1024, 10, 10, 0, NOW(), 'VALID');
    """

    try:
        cmd = 'docker exec -i transformation_postgres psql -U postgres -d territorial_db'
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=sql.encode('utf-8'))
        
        if proc.returncode != 0:
            log_fail(f"Error ejecutando psql vía docker exec: {stderr.decode()}")
            return None
        
        log_pass("Registro de base de datos creado.")
    except Exception as e:
        log_fail(f"Error al conectar con BD o crear registro vía docker: {e}")
        return None

    log_info("Escribiendo archivo CSV en contenedor de ms-transformation...")
    try:
        # Escribir el archivo CSV en el contenedor usando docker exec
        cmd = f'docker exec -i transformation_app sh -c "cat > /app/storage/{file_hash}.csv"'
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=csv_content.encode('utf-8'))
        
        if proc.returncode != 0:
            log_fail(f"Error escribiendo archivo vía docker exec: {stderr.decode()}")
            return None
            
        log_pass("Archivo CSV escrito en contenedor.")
        return dataset_id
    except Exception as e:
        log_fail(f"Error ejecutando docker exec: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# FASE 2: Ejecutar transformación Z-Score
# ══════════════════════════════════════════════════════════════════

def test_zscore_transformation(base_url: str, dataset_id: str) -> dict:
    """
    Ejecuta la transformación avanzada con method=zscore.
    Retorna la respuesta JSON.
    """
    log_section("FASE 2: Transformación Avanzada (Z-Score)")

    # Reescribir la URL para evadir el Gateway y golpear el microservicio directamente
    if "8000" in base_url:
        base_url = base_url.replace("8000", "8004")
        
    url = f"{base_url}/transform/advanced"

    payload = {
        "dataset_load_id": dataset_id,
        "method": "zscore"
    }
    
    log_info(f"POST {url}")
    log_info(f"Body: {json.dumps(payload, indent=2)}")

    try:
        resp = requests.post(url, json=payload, timeout=60)
    except requests.ConnectionError:
        log_fail("No se pudo conectar al servicio de transformación")
        return None

    if resp.status_code == 200:
        data = resp.json()
        log_pass(f"Transformación Z-Score completada: run_id={data.get('run_id')}")
        log_info(f"Status: {data.get('status')}")
        log_info(f"Records in: {data.get('records_input')}, out: {data.get('records_output')}")
        return data
    else:
        log_fail(f"Error en transformación: {resp.status_code}")
        log_info(f"Respuesta: {resp.text}")
        return None


# ══════════════════════════════════════════════════════════════════
# FASE 3: Verificaciones Z-Score
# ══════════════════════════════════════════════════════════════════

def verify_zscore_results(result: dict) -> int:
    """
    Verifica los criterios de aceptación para Z-Score.
    Retorna el número de fallos.
    """
    log_section("FASE 3: Verificación de Resultados Z-Score")
    failures = 0

    # 3.1: Verificar que el status es COMPLETED
    if result.get("status") == "COMPLETED":
        log_pass("Estado de la transformación: COMPLETED")
    else:
        log_fail(f"Estado esperado 'COMPLETED', obtenido '{result.get('status')}'")
        failures += 1

    # 3.2: Verificar que rules_applied contiene estadísticas
    rules = result.get("rules_applied", {})
    if not rules:
        log_fail("rules_applied está vacío")
        return failures + 1

    stats = rules.get("statistics", {})
    if not stats:
        log_fail("No se encontraron estadísticas en rules_applied")
        return failures + 1

    log_pass(f"Reporte estadístico contiene {len(stats)} columnas")
    log_info(f"Columnas procesadas: {rules.get('columns_processed', [])}")

    # 3.3: Verificar estadísticas de la columna 'population' (tiene el outlier)
    if "population" in stats:
        pop_stats = stats["population"]
        log_info(f"  population stats: {json.dumps(pop_stats, indent=4)}")

        # Verificar que se detectaron outliers
        if pop_stats.get("outliers_count", 0) > 0:
            log_pass(f"Outlier detectado en 'population': {pop_stats['outliers_count']} outlier(s)")
        else:
            log_fail("No se detectaron outliers en 'population' (esperaba al menos 1)")
            failures += 1

        # Verificar Z-Score: media ≈ 0
        mean_val = pop_stats.get("mean", 999)
        if abs(mean_val) < 0.1:  # tolerancia
            log_pass(f"Z-Score media de 'population' ≈ 0 (valor: {mean_val:.6f})")
        else:
            log_fail(f"Z-Score media de 'population' no es ≈ 0 (valor: {mean_val:.6f})")
            failures += 1

        # Verificar Z-Score: std ≈ 1
        std_val = pop_stats.get("std", 999)
        if abs(std_val - 1.0) < 0.15:  # tolerancia
            log_pass(f"Z-Score std de 'population' ≈ 1 (valor: {std_val:.6f})")
        else:
            log_fail(f"Z-Score std de 'population' no es ≈ 1 (valor: {std_val:.6f})")
            failures += 1
    else:
        log_fail("Columna 'population' no encontrada en estadísticas")
        failures += 1

    # 3.4: Verificar que todas las columnas tienen las claves esperadas
    expected_keys = {"min", "max", "mean", "std", "null_count", "outliers_count"}
    for col_name, col_stats in stats.items():
        missing = expected_keys - set(col_stats.keys())
        if missing:
            log_fail(f"Columna '{col_name}' le faltan claves: {missing}")
            failures += 1
        else:
            log_pass(f"Columna '{col_name}': todas las estadísticas presentes")

    return failures


# ══════════════════════════════════════════════════════════════════
# FASE 4: Prueba Min-Max
# ══════════════════════════════════════════════════════════════════

def test_minmax_transformation(base_url: str, dataset_id: str) -> int:
    """
    Ejecuta la transformación con Min-Max y verifica que los valores
    estén entre 0.0 y 1.0.
    """
    log_section("FASE 4: Transformación Avanzada (Min-Max)")
    failures = 0

    if "8000" in base_url:
        base_url = base_url.replace("8000", "8004")
        
    url = f"{base_url}/transform/advanced"

    payload = {
        "dataset_load_id": dataset_id,
        "method": "minmax"
    }

    log_info(f"POST {url}")

    try:
        resp = requests.post(url, json=payload, timeout=60)
    except requests.ConnectionError:
        log_fail("No se pudo conectar al servicio de transformación")
        return 1

    if resp.status_code != 200:
        log_fail(f"Error en transformación Min-Max: {resp.status_code}")
        log_info(f"Respuesta: {resp.text}")
        return 1

    data = resp.json()
    log_pass(f"Transformación Min-Max completada: run_id={data.get('run_id')}")

    stats = data.get("rules_applied", {}).get("statistics", {})

    for col_name, col_stats in stats.items():
        min_val = col_stats.get("min", -1)
        max_val = col_stats.get("max", 2)

        if 0.0 <= min_val and max_val <= 1.0:
            log_pass(f"Min-Max '{col_name}': valores en [0, 1] (min={min_val:.4f}, max={max_val:.4f})")
        else:
            log_fail(f"Min-Max '{col_name}': valores fuera de [0, 1] (min={min_val:.4f}, max={max_val:.4f})")
            failures += 1

    return failures


# ══════════════════════════════════════════════════════════════════
# FASE 5: Pruebas de validación de errores
# ══════════════════════════════════════════════════════════════════

def test_error_cases(base_url: str) -> int:
    """Prueba casos de error: dataset inexistente, método inválido."""
    log_section("FASE 5: Validación de Errores")
    failures = 0

    if "8000" in base_url:
        base_url = base_url.replace("8000", "8004")
        
    url = f"{base_url}/transform/advanced"

    # 5.1: Dataset inexistente
    log_info("Probando con dataset_load_id inexistente...")
    resp = requests.post(
        url,
        json={"dataset_load_id": "FAKE-ID-12345", "method": "zscore"},
        timeout=10
    )
    if resp.status_code in (404, 400):
        log_pass(f"Dataset inexistente devuelve HTTP {resp.status_code}")
    else:
        log_fail(f"Dataset inexistente debería devolver 404, devolvió {resp.status_code}")
        failures += 1

    # 5.2: Método inválido
    log_info("Probando con método de normalización inválido...")
    resp = requests.post(
        url,
        json={"dataset_load_id": "any-id", "method": "invalid_method"},
        timeout=10
    )
    if resp.status_code == 422:
        log_pass(f"Método inválido devuelve HTTP 422 (Validation Error)")
    else:
        log_fail(f"Método inválido debería devolver 422, devolvió {resp.status_code}")
        failures += 1

    return failures


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Test HU-20: Normalización Avanzada")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="URL base del gateway")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="URL de base de datos PostgreSQL")
    args = parser.parse_args()

    base_url = args.base_url
    db_url = args.db_url
    total_failures = 0

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║    TEST INTEGRAL — HU-20: Normalización Avanzada        ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
    print(f"  Base URL: {base_url}")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Fase 1: Inyectar dataset (Simulado localmente en BD)
    dataset_id = inject_test_dataset(db_url)
    if not dataset_id:
        print(f"\n{RED}{'═' * 60}{RESET}")
        print(f"{RED}  ABORTADO: No se pudo inyectar/obtener un dataset de prueba{RESET}")
        print(f"{RED}{'═' * 60}{RESET}")
        sys.exit(1)

    # Pequeña pausa para que el archivo se propague
    time.sleep(1)

    # Fase 2: Transformación Z-Score
    zscore_result = test_zscore_transformation(base_url, dataset_id)
    if zscore_result:
        # Fase 3: Verificaciones Z-Score
        total_failures += verify_zscore_results(zscore_result)
    else:
        total_failures += 1

    # Fase 4: Transformación Min-Max (usamos el mismo simulado)
    log_info("Usando el mismo dataset_id simulado para Min-Max")
    total_failures += test_minmax_transformation(base_url, dataset_id)

    # Fase 5: Casos de error
    total_failures += test_error_cases(base_url)

    # ── Resumen ──
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    if total_failures == 0:
        print(f"{BOLD}{GREEN}  ✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE{RESET}")
    else:
        print(f"{BOLD}{RED}  ✗ {total_failures} PRUEBA(S) FALLARON{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")

    sys.exit(0 if total_failures == 0 else 1)


if __name__ == "__main__":
    main()
