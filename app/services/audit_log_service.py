"""
Audit Logging Service.
Persists structured audit events to SQLite database with secret redaction and search/filtering capabilities.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.document import AuditLog
from app.core.logging import logger

SENSITIVE_KEYS = {"api_key", "password", "secret", "token", "authorization", "x-api-key"}

def sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Strips secrets, passwords, and sensitive tokens from audit metadata."""
    if not meta:
        return {}
    clean_meta = {}
    for k, v in meta.items():
        if k.lower() in SENSITIVE_KEYS:
            clean_meta[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean_meta[k] = sanitize_metadata(v)
        else:
            clean_meta[k] = v
    return clean_meta

class AuditLogService:
    def log_event(
        self,
        db: Session,
        request_id: str,
        endpoint: str,
        http_method: str,
        status_code: int,
        duration_ms: float,
        action: Optional[str] = None,
        document_id: Optional[str] = None,
        client_identifier: Optional[str] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Creates and persists a sanitized audit log record.
        """
        log_id = f"audit-{uuid.uuid4().hex[:12]}"
        clean_meta = sanitize_metadata(metadata)

        audit_entry = AuditLog(
            log_id=log_id,
            timestamp=datetime.now(timezone.utc),
            request_id=request_id,
            client_identifier=client_identifier or "anonymous",
            endpoint=endpoint,
            http_method=http_method,
            action=action or endpoint,
            document_id=document_id,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error_type=error_type,
            metadata_json=json.dumps(clean_meta) if clean_meta else None
        )

        db.add(audit_entry)
        try:
            db.commit()
            db.refresh(audit_entry)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save audit log: {e}")

        return audit_entry

    def get_logs(
        self,
        db: Session,
        endpoint: Optional[str] = None,
        action: Optional[str] = None,
        document_id: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Queries audit logs with optional filters and pagination.
        """
        query = db.query(AuditLog)

        if endpoint:
            query = query.filter(AuditLog.endpoint.ilike(f"%{endpoint}%"))
        if action:
            query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        if document_id:
            query = query.filter(AuditLog.document_id == document_id)
        if success_only is not None:
            query = query.filter(AuditLog.success == success_only)

        query = query.order_by(AuditLog.timestamp.desc())
        logs = query.offset(offset).limit(limit).all()
        return [log.to_dict() for log in logs]

audit_log_service = AuditLogService()
