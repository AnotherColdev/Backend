from sqlalchemy.orm import Session
from fastapi import Depends
from app.core.database import get_db
from app.repository.audit import AuditRepository
from app.services.audit import AuditService
from app.interfaces.audit_repo import IAuditRepository
from app.interfaces.audit_service import IAuditService

def get_audit_repository(db: Session = Depends(get_db)) -> IAuditRepository:
    return AuditRepository(db)

def get_audit_service(repo: IAuditRepository = Depends(get_audit_repository)) -> IAuditService:
    return AuditService(repo)
