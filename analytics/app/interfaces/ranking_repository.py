from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from app.models.ranking import ZoneScore, ScoreExecution


class IRankingRepository(ABC):
    """
    Interfaz del repositorio de ranking.
    DIP: el servicio depende de esta abstracción, no de la implementación concreta.
    OCP: se puede extender con nuevas implementaciones sin modificar el servicio.
    """

    @abstractmethod
    def get_by_execution(
        self,
        execution_id: str,
        level: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[List[ZoneScore], int]:
        """Retorna zonas y total para un execution_id dado."""
        ...

    @abstractmethod
    def get_execution(self, execution_id: str) -> Optional[ScoreExecution]:
        """Retorna metadata de una ejecución de scoring."""
        ...

    @abstractmethod
    def get_mock_data(
        self,
        execution_id: str,
        level: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[List[dict], int]:
        """Retorna datos mock cuando no hay BD disponible."""