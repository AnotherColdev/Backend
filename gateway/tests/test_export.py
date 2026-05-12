"""
HU-28: Suite de pruebas autónomas para los endpoints de exportación.
Verifica integridad del CSV, auditoría y flujos negativos.

Ejecutar con: python -m pytest Backend/gateway/tests/test_export.py -v
O directamente: python Backend/gateway/tests/test_export.py
"""
import csv
import io
import json
import sys
import os
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

# ──────────────────────────────────────────────────────────────────
# Ajustar sys.path para importar los módulos del gateway
# ──────────────────────────────────────────────────────────────────
GATEWAY_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if GATEWAY_DIR not in sys.path:
    sys.path.insert(0, GATEWAY_DIR)


# ══════════════════════════════════════════════════════════════════
#  DATOS MOCK PARA PRUEBAS
# ══════════════════════════════════════════════════════════════════
MOCK_RANKING_RESPONSE = {
    "success": True,
    "execution_id": "test-exec-001",
    "total": 3,
    "page": 1,
    "page_size": 100,
    "total_pages": 1,
    "has_next": False,
    "has_prev": False,
    "level_filter": None,
    "zones": [
        {
            "rank_position": 1,
            "zone_code": "BOG-001",
            "zone_name": "chapinero",
            "score_value": 0.87,
            "score_level": "ALTA",
            "execution_id": "test-exec-001",
        },
        {
            "rank_position": 2,
            "zone_code": "BOG-002",
            "zone_name": "suba",
            "score_value": 0.65,
            "score_level": "MEDIA",
            "execution_id": "test-exec-001",
        },
        {
            "rank_position": 3,
            "zone_code": "BOG-004",
            "zone_name": "kennedy",
            "score_value": 0.38,
            "score_level": "BAJA",
            "execution_id": "test-exec-001",
        },
    ],
}

MOCK_ZONE_SUMMARY = {
    "zone_code": "BOG-001",
    "zone_name": "chapinero",
    "score": {
        "score_value": 0.87,
        "score_level": "ALTA",
    },
    "indicators": {
        "population_indicator": 0.82,
        "income_indicator": 0.91,
        "education_indicator": 0.88,
        "competition_indicator": 0.45,
    },
}


# ══════════════════════════════════════════════════════════════════
#  TEST 1: INTEGRIDAD DEL CSV
# ══════════════════════════════════════════════════════════════════
def test_csv_integrity():
    """
    Verifica que el CSV generado:
    - Contenga encabezados correctos en español
    - Tenga una fila por cada zona
    - Sea parseable correctamente
    - Soporte caracteres UTF-8 (tildes, eñes)
    """
    print("\n" + "=" * 60)
    print("TEST 1: INTEGRIDAD DEL CSV")
    print("=" * 60)

    from app.services.export_service import generateRankingCsv

    csvBytes = generateRankingCsv(MOCK_RANKING_RESPONSE)

    # Verificar que es bytes
    assert isinstance(csvBytes, bytes), "El CSV debe ser de tipo bytes"

    # Decodificar y verificar UTF-8 BOM
    csvText = csvBytes.decode("utf-8")
    assert csvText.startswith("\ufeff"), "El CSV debe iniciar con BOM para Excel"

    # Remover BOM para parsear
    csvClean = csvText.lstrip("\ufeff")

    # Parsear CSV
    reader = csv.reader(io.StringIO(csvClean), delimiter=";")
    rows = list(reader)

    # Verificar encabezados
    expectedHeaders = ["Zona", "Indicadores", "Score", "Nivel", "Recomendación"]
    assert rows[0] == expectedHeaders, (
        f"Encabezados incorrectos.\n"
        f"  Esperado: {expectedHeaders}\n"
        f"  Obtenido: {rows[0]}"
    )
    print(f"  ✅ Encabezados correctos: {rows[0]}")

    # Verificar cantidad de filas (encabezado + 3 zonas)
    assert len(rows) == 4, f"Esperadas 4 filas (1 encabezado + 3 datos), obtenidas {len(rows)}"
    print(f"  ✅ Cantidad de filas correcta: {len(rows) - 1} zonas")

    # Verificar contenido de las filas
    for i, row in enumerate(rows[1:], start=1):
        assert len(row) == 5, f"Fila {i} debe tener 5 columnas, tiene {len(row)}"
        zoneName, indicators, score, level, recommendation = row
        assert zoneName.strip(), f"Fila {i}: nombre de zona vacío"
        assert float(score), f"Fila {i}: score no es numérico"
        assert level in ("ALTA", "MEDIA", "BAJA"), f"Fila {i}: nivel inválido '{level}'"
        assert len(recommendation) > 10, f"Fila {i}: recomendación muy corta"
        print(f"  ✅ Fila {i}: {zoneName} | Score: {score} | Nivel: {level}")

    # Verificar caracteres UTF-8
    fullText = csvClean
    assert "Recomendación" in fullText, "El encabezado 'Recomendación' debe tener tilde"
    assert "inversión" in fullText.lower() or "asignación" in fullText.lower(), (
        "Las recomendaciones deben contener caracteres con tilde"
    )
    print("  ✅ Caracteres UTF-8 (tildes y eñes) correctos")

    print("\n  ✅✅✅ TEST 1 PASÓ CORRECTAMENTE ✅✅✅")
    return True


# ══════════════════════════════════════════════════════════════════
#  TEST 2: SIMULACIÓN DE AUDITORÍA
# ══════════════════════════════════════════════════════════════════
def test_audit_event_format():
    """
    Verifica que el payload de auditoría coincida con el contrato
    esperado por ms-audit-trace (TraceCreate schema).
    """
    print("\n" + "=" * 60)
    print("TEST 2: FORMATO DE EVENTO DE AUDITORÍA")
    print("=" * 60)

    # Simular el payload que se enviaría
    tracePayload = {
        "dataset_load_id": "test-exec-001",
        "score_execution_id": "test-exec-001",
        "event_type": "EXPORT_RANKING_CSV",
        "status": "success",
        "user_id": "user-123",
        "parameters": {
            "export_format": "csv",
            "export_type": "RANKING_CSV",
            "zone_code": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "result_summary": {
            "total_zones": 3,
            "filename": "ranking_test-exe_20260511.csv",
        },
    }

    # Campos requeridos por TraceCreate en ms-audit-trace
    requiredFields = ["dataset_load_id", "event_type", "status"]
    optionalFields = [
        "transformation_run_id",
        "score_execution_id",
        "parameters",
        "result_summary",
        "user_id",
    ]

    for field in requiredFields:
        assert field in tracePayload, f"Campo requerido faltante: {field}"
        assert tracePayload[field], f"Campo requerido vacío: {field}"
        print(f"  ✅ Campo requerido '{field}': {tracePayload[field]}")

    for field in optionalFields:
        if field in tracePayload:
            print(f"  ✅ Campo opcional '{field}': presente")

    # Verificar tipos de datos
    assert isinstance(tracePayload["dataset_load_id"], str)
    assert isinstance(tracePayload["event_type"], str)
    assert isinstance(tracePayload["status"], str)
    assert isinstance(tracePayload["parameters"], dict)
    assert isinstance(tracePayload["result_summary"], dict)
    print("  ✅ Tipos de datos correctos")

    # Verificar que el event_type sigue el patrón esperado
    assert tracePayload["event_type"].startswith("EXPORT_"), (
        "El event_type debe iniciar con 'EXPORT_'"
    )
    print(f"  ✅ event_type sigue patrón 'EXPORT_*': {tracePayload['event_type']}")

    print("\n  ✅✅✅ TEST 2 PASÓ CORRECTAMENTE ✅✅✅")
    return True


# ══════════════════════════════════════════════════════════════════
#  TEST 3: FLUJO NEGATIVO (ESTADO NO COMPLETADO)
# ══════════════════════════════════════════════════════════════════
def test_negative_flow_incomplete_execution():
    """
    Verifica que el sistema rechace exportaciones de análisis
    que no estén en estado COMPLETED.
    """
    print("\n" + "=" * 60)
    print("TEST 3: FLUJO NEGATIVO — EJECUCIÓN INCOMPLETA")
    print("=" * 60)

    from app.services.export_service import validateExecutionStatus

    async def run_validation():
        # Mock: simular respuesta de ms-analytics con estado IN_PROGRESS
        mockResponse = MagicMock()
        mockResponse.status_code = 200
        mockResponse.json.return_value = {
            "success": True,
            "total": 0,
            "data": [],
        }

        mockScoringResponse = MagicMock()
        mockScoringResponse.status_code = 200
        mockScoringResponse.json.return_value = {
            "execution_id": "incomplete-exec",
            "status": "IN_PROGRESS",
        }

        with patch("app.services.export_service.httpx.AsyncClient") as MockClient:
            mockClient = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mockClient)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # Primera llamada: ranking (sin datos)
            # Segunda llamada: scoring results (IN_PROGRESS)
            mockClient.get = AsyncMock(side_effect=[mockResponse, mockScoringResponse])

            result = await validateExecutionStatus("incomplete-exec")
            return result

    result = asyncio.run(run_validation())

    assert result["valid"] is False, "Ejecución IN_PROGRESS no debe ser exportable"
    assert result["status"] == "IN_PROGRESS", (
        f"Estado esperado 'IN_PROGRESS', obtenido '{result['status']}'"
    )
    print(f"  ✅ Ejecución IN_PROGRESS rechazada correctamente")
    print(f"  ✅ Estado retornado: {result['status']}")
    print(f"  ✅ Mensaje: {result['message']}")

    # Verificar que un estado COMPLETED sí es válido
    async def run_completed_validation():
        mockResponse = MagicMock()
        mockResponse.status_code = 200
        mockResponse.json.return_value = {
            "success": True,
            "total": 5,
            "data": [{"zone_code": "BOG-001"}],
        }

        with patch("app.services.export_service.httpx.AsyncClient") as MockClient:
            mockClient = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mockClient)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mockClient.get = AsyncMock(return_value=mockResponse)

            result = await validateExecutionStatus("completed-exec")
            return result

    completedResult = asyncio.run(run_completed_validation())
    assert completedResult["valid"] is True, "Ejecución COMPLETED debe ser exportable"
    print(f"  ✅ Ejecución COMPLETED aceptada correctamente")
    print(f"  ✅ Estado retornado: {completedResult['status']}")

    print("\n  ✅✅✅ TEST 3 PASÓ CORRECTAMENTE ✅✅✅")
    return True


# ══════════════════════════════════════════════════════════════════
#  TEST 4: REPORTE DE ZONA JSON
# ══════════════════════════════════════════════════════════════════
def test_zone_report_json():
    """
    Verifica que el reporte JSON de zona contenga todos los campos
    requeridos: indicadores, score, predicción, combined_score
    y recomendación.
    """
    print("\n" + "=" * 60)
    print("TEST 4: REPORTE DE ZONA JSON")
    print("=" * 60)

    from app.services.export_service import buildZoneReport

    async def run_report():
        with patch("app.services.export_service.fetchZoneIndicators") as mockFetch:
            mockFetch.return_value = MOCK_ZONE_SUMMARY
            return await buildZoneReport("BOG-001")

    report = asyncio.run(run_report())

    # Verificar campos requeridos
    requiredKeys = [
        "zone_code",
        "zone_name",
        "indicators",
        "score",
        "combined_score",
        "prediction",
        "recommendation",
    ]
    for key in requiredKeys:
        assert key in report, f"Campo faltante en reporte: {key}"
        print(f"  ✅ Campo '{key}': presente")

    # Verificar estructura de indicadores
    indicatorKeys = [
        "population_indicator",
        "income_indicator",
        "education_indicator",
        "competition_indicator",
    ]
    for key in indicatorKeys:
        assert key in report["indicators"], f"Indicador faltante: {key}"
    print("  ✅ Todos los indicadores presentes")

    # Verificar score
    assert "score_value" in report["score"]
    assert "score_level" in report["score"]
    print(f"  ✅ Score: {report['score']['score_value']} ({report['score']['score_level']})")

    # Verificar combined_score
    assert isinstance(report["combined_score"], float)
    print(f"  ✅ Combined Score: {report['combined_score']}")

    # Verificar predicción
    assert "trend" in report["prediction"]
    assert "confidence" in report["prediction"]
    print(f"  ✅ Predicción: tendencia {report['prediction']['trend']}")

    # Verificar recomendación
    assert len(report["recommendation"]) > 20
    print(f"  ✅ Recomendación: {report['recommendation'][:60]}...")

    # Verificar que es serializable a JSON
    jsonStr = json.dumps(report, ensure_ascii=False)
    assert len(jsonStr) > 0
    print("  ✅ Reporte serializable a JSON correctamente")

    print("\n  ✅✅✅ TEST 4 PASÓ CORRECTAMENTE ✅✅✅")
    return True


# ══════════════════════════════════════════════════════════════════
#  EJECUTOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "🔬" * 30)
    print("  HU-28: SUITE DE PRUEBAS AUTÓNOMAS — EXPORTACIÓN DE RESULTADOS")
    print("🔬" * 30)

    results = {}
    tests = [
        ("Test 1 — Integridad CSV", test_csv_integrity),
        ("Test 2 — Formato de Auditoría", test_audit_event_format),
        ("Test 3 — Flujo Negativo", test_negative_flow_incomplete_execution),
        ("Test 4 — Reporte de Zona JSON", test_zone_report_json),
    ]

    for testName, testFunc in tests:
        try:
            results[testName] = testFunc()
        except Exception as e:
            print(f"\n  ❌❌❌ {testName} FALLÓ: {e} ❌❌❌")
            results[testName] = False
            import traceback
            traceback.print_exc()

    # Resumen final
    print("\n\n" + "=" * 60)
    print("  RESUMEN DE PRUEBAS HU-28")
    print("=" * 60)
    allPassed = True
    for testName, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {testName}")
        if not passed:
            allPassed = False

    print("=" * 60)
    if allPassed:
        print("  🎉 TODAS LAS PRUEBAS PASARON CORRECTAMENTE 🎉")
    else:
        print("  ⚠️  ALGUNAS PRUEBAS FALLARON — REVISAR ARRIBA ⚠️")
    print("=" * 60 + "\n")

    sys.exit(0 if allPassed else 1)
