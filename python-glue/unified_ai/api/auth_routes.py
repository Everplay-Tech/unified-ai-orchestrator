"""Authentication and authorization routes"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
import uuid
import secrets

from ..security.auth import (
    require_auth,
    authenticate_jwt,
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_api_key,
    get_storage_backend,
    hash_password,
    verify_password,
    get_user_by_username,
    create_user as create_user_func,
)
from ..storage import create_storage_backend, DatabaseType
from ..config import load_config
from pathlib import Path

def get_storage():
    """Get storage backend"""
    config = load_config()
    db_type = DatabaseType(config.storage.db_type.lower())
    if db_type == DatabaseType.POSTGRESQL:
        return create_storage_backend(db_type, connection_string=config.storage.connection_string)
    else:
        return create_storage_backend(db_type, db_path=Path(config.storage.db_path))
from ..security.authorization import require_role, Role, require_permission, Permission
from ..security.audit import AuditLogger, AuditEventType, get_audit_logger

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request"""
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class RefreshRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Refresh token response"""
    access_token: str
    token_type: str = "bearer"


class CreateUserRequest(BaseModel):
    """Create user request"""
    username: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: str = Field("user", pattern="^(admin|user|readonly)$")


class CreateAPIKeyRequest(BaseModel):
    """Create API key request"""
    name: Optional[str] = Field(None, max_length=255)
    expires_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API key response"""
    id: str
    key: str  # Only shown once on creation
    name: Optional[str]
    expires_at: Optional[int]
    created_at: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    req: Request,
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """Login and get JWT tokens"""
    # Get user by username
    user = await get_user_by_username(request.username)
    
    if not user:
    await audit_logger.log_auth_failure(
        user_id=None,
        reason="User not found",
        ip_address=req.client.host if req.client else None,
    )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not user.get("password_hash"):
    await audit_logger.log_auth_failure(
        user_id=user["user_id"],
        reason="No password set",
        ip_address=req.client.host if req.client else None,
    )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not verify_password(request.password, user["password_hash"]):
    await audit_logger.log_auth_failure(
        user_id=user["user_id"],
        reason="Invalid password",
        ip_address=req.client.host if req.client else None,
    )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create tokens
    token_data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user.get("role", "user"),
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    await audit_logger.log_auth_success(
        user_id=user["user_id"],
        auth_method="password",
        ip_address=req.client.host if req.client else None,
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user.get("email"),
            "role": user.get("role", "user"),
        }
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: RefreshRequest,
    req: Request,
):
    """Refresh access token using refresh token"""
    try:
        payload = verify_token(request.refresh_token, "refresh")
        
        # Create new access token
        token_data = {
            "user_id": payload["user_id"],
            "username": payload["username"],
            "role": payload.get("role", "user"),
        }
        
        access_token = create_access_token(token_data)
        
        return RefreshResponse(access_token=access_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    user: Dict[str, Any] = Depends(require_auth),
    req: Request = None,
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """Logout (invalidate session)"""
    # In a full implementation, we'd blacklist the token in Redis
    # For now, we just log the logout
    await audit_logger.log_event(
        event_type=AuditEventType.AUTH_LOGOUT,
        user_id=user["user_id"],
        ip_address=req.client.host if req and req.client else None,
    )
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    user: Dict[str, Any] = Depends(require_auth),
):
    """Get current user information"""
    return {
        "user_id": user["user_id"],
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role", "user"),
    }


@router.post("/users", response_model=Dict[str, Any])
async def create_user(
    request: CreateUserRequest,
    admin_user: Dict[str, Any] = Depends(require_role(Role.ADMIN)),
    req: Request = None,
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """Create a new user (admin only)"""
    # Check if username already exists
    existing_user = await get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Create user
    user = await create_user_func(
        username=request.username,
        email=request.email,
        password=request.password,
        role=request.role,
    )
    
    await audit_logger.log_event(
        event_type=AuditEventType.ADMIN_ACTION,
        user_id=admin_user["user_id"],
        resource_type="user",
        resource_id=user["user_id"],
        details={"action": "create", "username": request.username, "role": request.role},
        ip_address=req.client.host if req and req.client else None,
    )
    
    return user


@router.post("/users/{user_id}/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    user_id: str,
    request: CreateAPIKeyRequest,
    current_user: Dict[str, Any] = Depends(require_auth),
    req: Request = None,
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """Create an API key for a user"""
    # Check if user can create API keys for this user
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create API keys for other users"
        )
    
    # Generate API key
    api_key = secrets.token_urlsafe(32)
    api_key_hash = hash_api_key(api_key)
    
    # Calculate expiration
    expires_at = None
    if request.expires_days:
        from datetime import datetime, timedelta
        expires_at = int((datetime.now() + timedelta(days=request.expires_days)).timestamp())
    
    # Store API key
    storage = get_storage()
    await storage.initialize()
    
    key_id = str(uuid.uuid4())
    await storage.create_api_key(
        key_id=key_id,
        user_id=user_id,
        key_hash=api_key_hash,
        name=request.name,
        expires_at=expires_at,
    )
    
    await storage.close()
    
    await audit_logger.log_event(
        event_type=AuditEventType.RESOURCE_CREATE,
        user_id=current_user["user_id"],
        resource_type="api_key",
        resource_id=key_id,
        details={"user_id": user_id, "name": request.name},
        ip_address=req.client.host if req and req.client else None,
    )
    
    return APIKeyResponse(
        id=key_id,
        key=api_key,  # Only shown once
        name=request.name,
        expires_at=expires_at,
        created_at=datetime.now().isoformat(),
    )


@router.delete("/users/{user_id}/api-keys/{key_id}")
async def revoke_api_key(
    user_id: str,
    key_id: str,
    current_user: Dict[str, Any] = Depends(require_auth),
    req: Request = None,
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """Revoke an API key"""
    # Check if user can revoke API keys for this user
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke API keys for other users"
        )
    
    # Revoke API key
    storage = get_storage()
    await storage.initialize()
    
    await storage.revoke_api_key(key_id)
    
    await storage.close()
    
    await audit_logger.log_event(
        event_type=AuditEventType.RESOURCE_DELETE,
        user_id=current_user["user_id"],
        resource_type="api_key",
        resource_id=key_id,
        details={"user_id": user_id},
        ip_address=req.client.host if req and req.client else None,
    )
    
    return {"message": "API key revoked"}


@router.get("/users/{user_id}/api-keys", response_model=List[Dict[str, Any]])
async def list_api_keys(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_auth),
):
    """List API keys for a user"""
    # Check if user can list API keys for this user
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot list API keys for other users"
        )
    
    # Get API keys
    storage = get_storage()
    await storage.initialize()
    
    api_keys = await storage.list_api_keys(user_id)
    
    await storage.close()
    
    return api_keys


@router.get("/audit/logs", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin_user: Dict[str, Any] = Depends(require_role(Role.ADMIN)),
):
    """Get audit logs (admin only)"""
    storage = get_storage()
    await storage.initialize()
    
    logs = await storage.get_audit_logs(
        user_id=user_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    
    await storage.close()
    
    return logs
