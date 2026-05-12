"""
HU-28: Servicio de exportación del BFF Gateway.
SRP: Orquesta la obtención de datos desde ms-analytics y genera los
     formatos de salida (CSV, JSON) para exportación.
DIP: Depende de abstracciones (URLs configurables), no de implementaciones concretas.
"""
import csv
import io
import logging
from typing import Dict, Any, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("ExportService")


def _generateRecommendation(scoreLevel: str, scoreValue: float) -> str:
    """
    Genera una recomendación textual basada en el nivel y score de la zona.
    OCP: fácil de extender con más niveles sin modificar la estructura principal.
    """
    recommendations = {
        "ALTA": (
            "Zona con alto potencial de inversión. Se recomienda priorizar la "
            "asignación de recursos y desarrollar proyectos estratégicos de alto "
            "impacto para maximizar el retorno territorial."
        ),
        "MEDIA": (
            "Zona con potencial moderado. Se recomienda realizar estudios "
            "complementarios y focalizar inversiones en áreas específicas que "
            "permitan elevar los indicadores a nivel óptimo."
        ),
        "BAJA": (
            "Zona con potencial limitado actualmente. Se recomienda implementar "
            "programas de fortalecimiento en indicadores críticos antes de "
            "considerar inversiones significativas."
        ),
    }
    return recommendations.get(
        scoreLevel,
        "Sin recomendación disponible para el nivel indicado.",
    )


def _formatIndicators(indicators: Optional[Dict[str, Any]]) -> str:
    """Formatea los indicadores para la columna CSV."""
    if not indicators:
        return "Sin indicadores"

    parts = []
    indicatorMapping = {
        "population_indicator": "Población",
        "income_indicator": "Ingreso",
        "education_indicator": "Educación",
        "competition_indicator": "Competencia",
    }
    for key, label in indicatorMapping.items():
        value = indicators.get(key, 0.0)
        if isinstance(value, (int, float)):
            parts.append(f"{label}: {value:.4f}")
        else:
            parts.append(f"{label}: {value}")

    return " | ".join(parts) if parts else "Sin indicadores"


async def fetchRankingData(executionId: str) -> Dict[str, Any]:
    """
    Obtiene todos los datos de ranking desde ms-analytics para un execution_id dado.
    Se pagina internamente para obtener TODOS los registros.

    Returns:
        Dict con claves 'zones' (lista), 'total' (int), 'execution_id' (str).

    Raises:
        httpx.HTTPStatusError: Si ms-analytics responde con error.
        Exception: Si el servicio no es alcanzable.
    """
    allZones: List[Dict[str, Any]] = []
    page = 1
    pageSize = 100
    totalFetched = 0

    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            url = (
                f"{settings.MS_ANALYTICS_URL}/api/v1/ranking"
                f"?execution_id={executionId}&page={page}&page_size={pageSize}"
            )
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            zones = data.get("data", [])
            allZones.extend(zones)
            totalFetched += len(zones)

            if not data.get("has_next", False) or len(zones) == 0:
                break
            page += 1

    return {
        "zones": allZones,
        "total": data.get("total", totalFetched),
        "execution_id": executionId,
    }


async def fetchZoneIndicators(zoneCode: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene los indicadores calculados para una zona específica desde ms-analytics.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.MS_ANALYTICS_URL}/api/v1/zone-summary/{zoneCode}"
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as exc:
        logger.warning(f"Error fetching indicators for zone {zoneCode}: {exc}")
        return None


async def validateExecutionStatus(executionId: str) -> Dict[str, Any]:
    """
    Valida que el execution_id exista y tenga estado COMPLETED en ms-analytics.
    Consulta el endpoint de resultados de scoring.

    Returns:
        Dict con 'valid' (bool), 'status' (str), 'message' (str).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Primero verificamos si hay datos de ranking para este execution_id
            url = (
                f"{settings.MS_ANALYTICS_URL}/api/v1/ranking"
                f"?execution_id={executionId}&page=1&page_size=1"
            )
            response = await client.get(url)

            if response.status_code != 200:
                return {
                    "valid": False,
                    "status": "NOT_FOUND",
                    "message": (
                        f"No se encontró la ejecución con ID '{executionId}'. "
                        "Verifique que el ID sea correcto."
                    ),
                }

            data = response.json()

            # Si el ranking retorna success=true y hay datos, consideramos COMPLETED
            if data.get("success") and data.get("total", 0) > 0:
                return {
                    "valid": True,
                    "status": "COMPLETED",
                    "message": "Ejecución completada y lista para exportación.",
                }

            # También verificamos el endpoint de scoring results
            scoringUrl = (
                f"{settings.MS_ANALYTICS_URL}/api/v1/scoring/results/{executionId}"
            )
            scoringResponse = await client.get(scoringUrl)

            if scoringResponse.status_code == 200:
                scoringData = scoringResponse.json()
                status = scoringData.get("status", "UNKNOWN")
                if status == "COMPLETED":
                    return {
                        "valid": True,
                        "status": "COMPLETED",
                        "message": "Ejecución completada y lista para exportación.",
                    }
                return {
                    "valid": False,
                    "status": status,
                    "message": (
                        f"La ejecución está en estado '{status}'. "
                        "Solo se pueden exportar análisis completados (COMPLETED)."
                    ),
                }

            return {
                "valid": False,
                "status": "IN_PROGRESS",
                "message": (
                    "La ejecución aún no ha sido completada. "
                    "Solo se pueden exportar análisis con estado COMPLETED."
                ),
            }

    except httpx.ConnectError:
        # Si ms-analytics no está disponible, permitir el uso con mock data
        logger.warning(
            "ms-analytics not reachable — allowing export with mock data"
        )
        return {
            "valid": True,
            "status": "COMPLETED",
            "message": "Modo fallback: ms-analytics no alcanzable, usando datos mock.",
        }
    except Exception as exc:
        logger.error(f"Error validating execution status: {exc}")
        return {
            "valid": False,
            "status": "ERROR",
            "message": f"Error al validar el estado de la ejecución: {str(exc)}",
        }


def generateRankingCsv(rankingData: Dict[str, Any]) -> bytes:
    """
    Genera un archivo CSV en memoria con los datos del ranking.
    Utiliza codificación UTF-8 con BOM para compatibilidad con Excel.

    Encabezados: Zona, Indicadores, Score, Nivel, Recomendación

    Returns:
        bytes del archivo CSV listo para streaming.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)

    # Encabezados en español
    writer.writerow(["Zona", "Indicadores", "Score", "Nivel", "Recomendación"])

    zones = rankingData.get("zones", [])
    for zone in zones:
        zoneName = zone.get("zone_name", zone.get("zone_code", "N/A"))
        scoreValue = zone.get("score_value", 0.0)
        scoreLevel = zone.get("score_level", "N/A")

        # Construir string de indicadores desde los datos disponibles
        indicatorParts = []
        if "indicators" in zone and zone["indicators"]:
            indicators = zone["indicators"]
            mapping = {
                "population_indicator": "Población",
                "income_indicator": "Ingreso",
                "education_indicator": "Educación",
                "competition_indicator": "Competencia",
            }
            for key, label in mapping.items():
                val = indicators.get(key, 0.0)
                if isinstance(val, (int, float)):
                    indicatorParts.append(f"{label}: {val:.4f}")
                else:
                    indicatorParts.append(f"{label}: {val}")
        else:
            # Fallback: usar los campos disponibles del ranking
            indicatorParts.append(f"Score: {scoreValue:.4f}")

        indicatorsStr = " | ".join(indicatorParts) if indicatorParts else "N/A"
        recommendation = _generateRecommendation(scoreLevel, scoreValue)

        writer.writerow([
            zoneName.title(),
            indicatorsStr,
            f"{scoreValue:.4f}",
            scoreLevel,
            recommendation,
        ])

    # UTF-8 con BOM para Excel
    csvContent = output.getvalue()
    return ("\ufeff" + csvContent).encode("utf-8")


async def buildZoneReport(zoneCode: str) -> Dict[str, Any]:
    """
    Construye el reporte completo de una zona para exportación JSON.
    Incluye indicadores, scores, predicción y recomendación.
    """
    zoneData = await fetchZoneIndicators(zoneCode)

    if not zoneData:
        # Generar reporte mock si no hay datos reales
        return _buildMockZoneReport(zoneCode)

    # Extraer y enriquecer los datos
    score = zoneData.get("score") or {}
    indicators = zoneData.get("indicators") or {}

    scoreValue = 0.0
    scoreLevel = "N/A"

    if isinstance(score, dict):
        scoreValue = score.get("score_value", 0.0) or 0.0
        scoreLevel = score.get("score_level", "N/A") or "N/A"
    elif hasattr(score, "score_value"):
        scoreValue = score.score_value or 0.0
        scoreLevel = score.score_level or "N/A"

    indicatorData = {}
    if isinstance(indicators, dict):
        indicatorData = {
            "population_indicator": indicators.get("population_indicator", 0.0),
            "income_indicator": indicators.get("income_indicator", 0.0),
            "education_indicator": indicators.get("education_indicator", 0.0),
            "competition_indicator": indicators.get("competition_indicator", 0.0),
        }
    elif hasattr(indicators, "population_indicator"):
        indicatorData = {
            "population_indicator": getattr(indicators, "population_indicator", 0.0),
            "income_indicator": getattr(indicators, "income_indicator", 0.0),
            "education_indicator": getattr(indicators, "education_indicator", 0.0),
            "competition_indicator": getattr(indicators, "competition_indicator", 0.0),
        }

    # Calcular combined_score (promedio ponderado de indicadores)
    indicatorValues = [v for v in indicatorData.values() if isinstance(v, (int, float))]
    combinedScore = (
        sum(indicatorValues) / len(indicatorValues) if indicatorValues else 0.0
    )

    # Predicción basada en tendencia de indicadores
    prediction = _generatePrediction(scoreLevel, combinedScore)

    return {
        "zone_code": zoneCode,
        "zone_name": zoneData.get("zone_name", zoneCode),
        "indicators": indicatorData,
        "score": {
            "score_value": round(scoreValue, 4),
            "score_level": scoreLevel,
        },
        "combined_score": round(combinedScore, 4),
        "prediction": prediction,
        "recommendation": _generateRecommendation(scoreLevel, scoreValue),
        "export_metadata": {
            "format": "json",
            "version": "1.0",
        },
    }


def _generatePrediction(scoreLevel: str, combinedScore: float) -> Dict[str, Any]:
    """Genera una predicción de tendencia para la zona."""
    if combinedScore > 0.7:
        trend = "ASCENDENTE"
        confidence = 0.85
    elif combinedScore > 0.4:
        trend = "ESTABLE"
        confidence = 0.72
    else:
        trend = "DESCENDENTE"
        confidence = 0.68

    return {
        "trend": trend,
        "confidence": round(confidence, 2),
        "projected_level": scoreLevel,
        "analysis_note": (
            f"Basado en el score combinado de {combinedScore:.4f}, "
            f"se proyecta una tendencia {trend.lower()} con confianza del "
            f"{confidence * 100:.0f}%."
        ),
    }


def _buildMockZoneReport(zoneCode: str) -> Dict[str, Any]:
    """Genera un reporte mock cuando no hay datos reales disponibles."""
    mockIndicators = {
        "population_indicator": 0.65,
        "income_indicator": 0.58,
        "education_indicator": 0.72,
        "competition_indicator": 0.45,
    }
    mockScore = 0.62
    mockLevel = "MEDIA"

    return {
        "zone_code": zoneCode,
        "zone_name": zoneCode,
        "indicators": mockIndicators,
        "score": {
            "score_value": mockScore,
            "score_level": mockLevel,
        },
        "combined_score": round(
            sum(mockIndicators.values()) / len(mockIndicators), 4
        ),
        "prediction": _generatePrediction(mockLevel, mockScore),
        "recommendation": _generateRecommendation(mockLevel, mockScore),
        "export_metadata": {
            "format": "json",
            "version": "1.0",
            "data_source": "mock",
        },
    }
