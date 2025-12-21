"""Audit logging for security and compliance."""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for security events."""
    
    def __init__(self):
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Create file handler for audit logs
        import os
        audit_log_file = os.getenv("AUDIT_LOG_FILE", "./logs/audit.log")
        os.makedirs(os.path.dirname(audit_log_file), exist_ok=True)
        
        handler = logging.FileHandler(audit_log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.audit_logger.addHandler(handler)
    
    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        job_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "file_upload", "job_created", "result_accessed")
            user_id: User ID (if available)
            job_id: Job ID (if applicable)
            details: Additional event details
            ip_address: Client IP address
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "job_id": job_id,
            "ip_address": ip_address,
            "details": details or {}
        }
        
        self.audit_logger.info(json.dumps(audit_entry))
    
    def log_file_upload(self, job_id: str, filename: str, file_size: int, user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log file upload event."""
        self.log_event(
            event_type="file_upload",
            user_id=user_id,
            job_id=job_id,
            details={
                "filename": filename,
                "file_size": file_size
            },
            ip_address=ip_address
        )
    
    def log_job_access(self, job_id: str, user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log job access event."""
        self.log_event(
            event_type="job_access",
            user_id=user_id,
            job_id=job_id,
            ip_address=ip_address
        )
    
    def log_result_access(self, result_id: str, job_id: str, user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log result access event."""
        self.log_event(
            event_type="result_access",
            user_id=user_id,
            job_id=job_id,
            details={"result_id": result_id},
            ip_address=ip_address
        )
    
    def log_data_export(self, export_type: str, user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log data export event."""
        self.log_event(
            event_type="data_export",
            user_id=user_id,
            details={"export_type": export_type},
            ip_address=ip_address
        )
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Log security-related event (e.g., authentication failure, unauthorized access)."""
        self.log_event(
            event_type=f"security_{event_type}",
            user_id=user_id,
            details=details,
            ip_address=ip_address
        )


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


