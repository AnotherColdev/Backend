from typing import Optional, List
from app.schemas.schema import ZoneItem


# Datos de prueba — simulan lo que vendría de la BD
# Cada zona pertenece a un dataset con un estado
_MOCK_ZONES = [
    {"zone_code": "BOG-001", "zone_name": "chapinero",  "dataset_id": "ds-001", "dataset_status": "VALID"},
    {"zone_code": "BOG-002", "zone_name": "suba",        "dataset_id": "ds-001", "dataset_status": "VALID"},
    {"zone_code": "BOG-003", "zone_name": "usaquen",     "dataset_id": "ds-001", "dataset_status": "VALID"},
    {"zone_code": "BOG-004", "zone_name": "kennedy",     "dataset_id": "ds-002", "dataset_status": "INVALID"},   # ← no debe aparecer
    {"zone_code": "BOG-005", "zone_name": "engativa",    "dataset_id": "ds-003", "dataset_status": "UPLOADED"},  # ← no debe aparecer
    {"zone_code": "BOG-006", "zone_name": "bosa",        "dataset_id": "ds-001", "dataset_status": "VALID"},
]

# Estados que se consideran "listos para consultar"
VALID_STATUSES = {"VALID", "TRANSFORMED"}


class ZoneService:
    """
    Lógica de negocio para consulta de zonas.
    Principio SRP: solo maneja lógica de zonas.
    """

    def get_zones(
        self,
        dataset_id: Optional[str],
        limit: int,
        offset: int,
    ) -> dict:
        """
        Retorna zonas de datasets válidos, con paginación.
        """
        # Paso 1: obtener zonas filtradas por estado válido
        valid_zones = self._fetch_valid_zones(dataset_id)

        # Paso 2: calcular total antes de paginar
        total = len(valid_zones)

        # Paso 3: aplicar paginación
        paginated = valid_zones[offset: offset + limit]

        # Paso 4: calcular si hay más páginas disponibles
        # Ejemplo: total=6, offset=0, limit=3 → has_more=True (quedan 3)
        # Ejemplo: total=6, offset=3, limit=3 → has_more=False (no quedan más)
        has_more = (offset + limit) < total

        # Paso 5: convertir a objetos ZoneItem
        zone_items = [
            ZoneItem(zone_code=z["zone_code"], zone_name=z["zone_name"])
            for z in paginated
        ]

        return {
            "total": total,
            "has_more": has_more,
            "zones": zone_items,
        }

    def _fetch_valid_zones(self, dataset_id: Optional[str]) -> list:
        """
        Método privado.
        Filtra zonas que pertenezcan a datasets con estado válido.
        Si se pasa dataset_id, filtra también por ese dataset.
        """
        # Filtrar por estado válido (criterio de aceptación: no mostrar datos no procesados)
        zones = [
            z for z in _MOCK_ZONES
            if z["dataset_status"] in VALID_STATUSES
        ]

        # Si se pidió un dataset específico, filtrar también por ese
        if dataset_id:
            zones = [z for z in zones if z["dataset_id"] == dataset_id]

        return zones


# Instancia única del servicio
zone_service = ZoneService()