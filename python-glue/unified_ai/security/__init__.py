"""Security module: authentication, authorization, validation, encryption"""

from .auth import (
    authenticate_api_key,
    authenticate_jwt,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    require_auth,
)
from .authorization import (
    require_role,
    require_permission,
    check_resource_access,
    Role,
    Permission,
)
from .validation import (
    validate_input,
    sanitize_html,
    sanitize_path,
    validate_sql_safe,
    ValidationError,
)
from .encryption import (
    encrypt_secret,
    decrypt_secret,
    hash_password,
    verify_password,
)
from .audit import (
    AuditLogger,
    AuditEventType,
    get_audit_logger,
)

__all__ = [
    # Authentication
    "authenticate_api_key",
    "authenticate_jwt",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_current_user",
    "require_auth",
    # Authorization
    "require_role",
    "require_permission",
    "check_resource_access",
    "Role",
    "Permission",
    # Validation
    "validate_input",
    "sanitize_html",
    "sanitize_path",
    "validate_sql_safe",
    "ValidationError",
    # Encryption
    "encrypt_secret",
    "decrypt_secret",
    "hash_password",
    "verify_password",
    # Audit logging
    "AuditLogger",
    "AuditEventType",
    "get_audit_logger",
]
