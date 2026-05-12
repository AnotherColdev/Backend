from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogCreate

class IAuditService(ABC):
    @abstractmethod
    def log_action(self, trace_id: str, log_in: AuditLogCreate) -> AuditLog:
        pass

    @abstractmethod
    def get_logs(self, limit: int = 100, skip: int = 0) -> List[AuditLog]:
        pass

    @abstractmethod
    def get_user_logs(self, user_id: str, limit: int = 100, skip: int = 0) -> List[AuditLog]:
        pass
