"""Audit logging for security events"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from ..observability import get_logger

logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events"""
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    PERMISSION_DENIED = "permission.denied"
    RESOURCE_ACCESS = "resource.access"
    RESOURCE_CREATE = "resource.create"
    RESOURCE_UPDATE = "resource.update"
    RESOURCE_DELETE = "resource.delete"
    CONFIG_CHANGE = "config.change"
    ADMIN_ACTION = "admin.action"


class AuditLogger:
    """Audit logger for security events"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an audit event"""
        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }
        
        # Log as structured JSON
        self.logger.info(
            "Audit event",
            extra={"audit": event_data}
        )
    
    def log_auth_success(
        self,
        user_id: str,
        auth_method: str,
        ip_address: Optional[str] = None,
    ):
        """Log successful authentication"""
        self.log_event(
            event_type=AuditEventType.AUTH_SUCCESS,
            user_id=user_id,
            details={"auth_method": auth_method},
            ip_address=ip_address,
        )
    
    def log_auth_failure(
        self,
        user_id: Optional[str],
        reason: str,
        ip_address: Optional[str] = None,
    ):
        """Log failed authentication attempt"""
        self.log_event(
            event_type=AuditEventType.AUTH_FAILURE,
            user_id=user_id,
            details={"reason": reason},
            ip_address=ip_address,
        )
    
    def log_permission_denied(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        required_permission: str,
        ip_address: Optional[str] = None,
    ):
        """Log permission denied event"""
        self.log_event(
            event_type=AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details={"required_permission": required_permission},
            ip_address=ip_address,
        )
    
    def log_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: Optional[str] = None,
    ):
        """Log resource access"""
        self.log_event(
            event_type=AuditEventType.RESOURCE_ACCESS,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details={"action": action},
            ip_address=ip_address,
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
