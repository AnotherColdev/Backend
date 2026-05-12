import logging
from typing import List
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from app.interfaces.audit_repo import IAuditRepository
from app.interfaces.audit_service import IAuditService
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogCreate
from app.core.exceptions import DomainException

logger = logging.getLogger("AuditService")

class AuditService(IAuditService):
    def __init__(self, audit_repo: IAuditRepository):
        self.audit_repo = audit_repo

    # HU-09 Reintento ante fallos DB: Retry if an OperationalError or general SQLAlchemyError occurs
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(SQLAlchemyError),
        reraise=True
    )
    def _create_log_with_retry(self, log_entry: AuditLog) -> AuditLog:
        try:
            return self.audit_repo.create(log_entry)
        except SQLAlchemyError as err:
            logger.warning(f"Database error while saving audit log. Retrying... Exception: {str(err)}")
            raise err

    def log_action(self, trace_id: str, log_in: AuditLogCreate) -> AuditLog:
        new_log = AuditLog(
            trace_id=trace_id,
            service_name=log_in.service_name,
            action=log_in.action,
            user_id=log_in.user_id,
            details=log_in.details
        )
        
        try:
            # Invoking the retryable method
            saved_log = self._create_log_with_retry(new_log)
            return saved_log
        except Exception as e:
            logger.error(f"Failed to save audit log after multiple retries. Details: {log_in.model_dump_json()} Exception: {str(e)}")
            raise DomainException(f"Could not persist audit log: {str(e)}", status_code=500)

    def get_logs(self, limit: int = 100, skip: int = 0) -> List[AuditLog]:
        return self.audit_repo.get_all(limit=limit, skip=skip)

    def get_user_logs(self, user_id: str, limit: int = 100, skip: int = 0) -> List[AuditLog]:
        return self.audit_repo.get_by_user(user_id=user_id, limit=limit, skip=skip)
