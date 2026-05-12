from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["Observabilidad"])


@router.get(
    "/health",
    summary="Health check del servicio",
    description="Verifica si el servicio está activo y con conexión a base de datos.",
)
def health_check():
    # Verificar conexión a BD
    db_connected = _check_database()

    # Construir respuesta
    response = {
        "status": "healthy" if db_connected else "unhealthy",
        "service_name": "ms-ingestion",
        "version": "1.0.0",
        "db_connected": db_connected,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Si la BD no está conectada, retornar 503
    if not db_connected:
        from fastapi import Response
        return Response(
            content=str(response),
            status_code=503,
        )

    return response


def _check_database() -> bool:
    """
    Verifica si la base de datos está disponible.
    Por ahora retorna True (simulado).
    Cuando haya BD real: ejecutar SELECT 1 y capturar errores.
    """
    try:
        # Cuando haya BD real sería algo como:
        # db.execute("SELECT 1")
        return True
    except Exception:
        return False