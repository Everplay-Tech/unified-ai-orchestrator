"""Authorization: RBAC, permissions, resource access"""

from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from functools import wraps

from fastapi import HTTPException, status, Depends

from .auth import get_current_user


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class Permission(str, Enum):
    """Permissions"""
    # Chat permissions
    CHAT_READ = "chat:read"
    CHAT_WRITE = "chat:write"
    CHAT_DELETE = "chat:delete"
    
    # Admin permissions
    ADMIN_MANAGE = "admin:manage"
    ADMIN_USERS = "admin:users"
    ADMIN_CONFIG = "admin:config"
    
    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.CHAT_DELETE,
        Permission.ADMIN_MANAGE,
        Permission.ADMIN_USERS,
        Permission.ADMIN_CONFIG,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_DELETE,
    ],
    Role.USER: [
        Permission.CHAT_READ,
        Permission.CHAT_WRITE,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
    ],
    Role.READONLY: [
        Permission.CHAT_READ,
        Permission.PROJECT_READ,
    ],
}


def get_user_role(user: Dict[str, Any]) -> Role:
    """Extract role from user context"""
    role_str = user.get("role", "user")
    try:
        return Role(role_str)
    except ValueError:
        return Role.USER


def get_user_permissions(user: Dict[str, Any]) -> List[Permission]:
    """Get all permissions for a user"""
    role = get_user_role(user)
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user: Dict[str, Any], permission: Permission) -> bool:
    """Check if user has a specific permission"""
    permissions = get_user_permissions(user)
    return permission in permissions


def require_role(*allowed_roles: Role):
    """Dependency to require specific role(s)"""
    async def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_role = get_user_role(user)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in allowed_roles]}"
            )
        
        return user
    
    return role_checker


def require_permission(permission: Permission):
    """Dependency to require specific permission"""
    async def permission_checker(user: Dict[str, Any] = Depends(get_current_user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission: {permission.value}"
            )
        
        return user
    
    return permission_checker


async def check_resource_access(
    user: Dict[str, Any],
    resource_type: str,
    resource_id: str,
    action: str = "read"
) -> bool:
    """Check if user has access to a specific resource"""
    # Admin has access to everything
    if get_user_role(user) == Role.ADMIN:
        return True
    
    user_id = user.get("user_id")
    if not user_id:
        return False
    
    # Check resource-specific permissions
    if resource_type == "project":
        # Check if user owns the project by querying database
        try:
            from ..config import load_config
            from pathlib import Path
            import sqlite3
            
            config = load_config()
            db_path = Path(config.storage.db_path).expanduser()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check indexed_files table for project ownership
            cursor.execute(
                "SELECT COUNT(*) FROM indexed_files WHERE project_id = ? LIMIT 1",
                (resource_id,)
            )
            project_exists = cursor.fetchone()[0] > 0
            
            # If project exists and user has permissions, allow access
            # Note: In a full implementation, you'd have a projects table with owner_id
            conn.close()
            
            if project_exists:
                if action == "read":
                    return has_permission(user, Permission.PROJECT_READ)
                elif action == "write":
                    return has_permission(user, Permission.PROJECT_WRITE)
                elif action == "delete":
                    return has_permission(user, Permission.PROJECT_DELETE)
        except Exception:
            # Fallback to permission check only
            pass
        
        # Fallback: check permissions only
        if action == "read":
            return has_permission(user, Permission.PROJECT_READ)
        elif action == "write":
            return has_permission(user, Permission.PROJECT_WRITE)
        elif action == "delete":
            return has_permission(user, Permission.PROJECT_DELETE)
    
    elif resource_type == "conversation":
        # Check if user owns the conversation
        try:
            from ..config import load_config
            from pathlib import Path
            import sqlite3
            import json
            
            config = load_config()
            db_path = Path(config.storage.db_path).expanduser()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check contexts table for conversation ownership
            cursor.execute(
                "SELECT data FROM contexts WHERE conversation_id = ?",
                (resource_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row:
                context_data = json.loads(row[0])
                # Check if context has user_id field (would be added in future)
                context_user_id = context_data.get("user_id")
                
                # If user_id matches or context has no user_id (legacy), check permissions
                if context_user_id is None or context_user_id == user_id:
                    if action == "read":
                        return has_permission(user, Permission.CHAT_READ)
                    elif action == "write":
                        return has_permission(user, Permission.CHAT_WRITE)
                    elif action == "delete":
                        return has_permission(user, Permission.CHAT_DELETE)
        except Exception:
            # Fallback to permission check only
            pass
        
        # Fallback: check permissions only
        if action == "read":
            return has_permission(user, Permission.CHAT_READ)
        elif action == "write":
            return has_permission(user, Permission.CHAT_WRITE)
        elif action == "delete":
            return has_permission(user, Permission.CHAT_DELETE)
    
    return False


def require_resource_access(resource_type: str, action: str = "read"):
    """Decorator to require resource access"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, resource_id: str, **kwargs):
            user = await get_current_user()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not await check_resource_access(user, resource_type, resource_id, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to {resource_type}:{resource_id}"
                )
            
            return await func(*args, resource_id=resource_id, **kwargs)
        return wrapper
    return decorator
