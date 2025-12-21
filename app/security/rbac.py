"""Role-Based Access Control (RBAC) utilities."""
import os
from typing import Optional, List
from functools import wraps
from fastapi import HTTPException, status

# RBAC configuration
RBAC_ENABLED = os.getenv("RBAC_ENABLED", "false").lower() == "true"

# Role definitions
ROLES = {
    "admin": ["read", "write", "delete", "export", "admin"],
    "user": ["read", "write"],
    "viewer": ["read"],
    "api": ["read", "write"]  # For API keys
}

# Permissions
PERMISSIONS = {
    "read": ["get_job", "get_result", "list_jobs"],
    "write": ["create_job", "upload_file"],
    "delete": ["delete_job", "delete_result"],
    "export": ["export_active_learning", "export_results"],
    "admin": ["manage_users", "manage_settings"]
}


def get_user_role(user_id: Optional[str] = None) -> str:
    """
    Get user role.
    In production, this would query a user database.
    For now, returns default role based on configuration.
    """
    if not RBAC_ENABLED:
        return "user"  # Default role when RBAC is disabled
    
    # TODO: Implement actual user role lookup from database
    # For now, return default
    return os.getenv("DEFAULT_USER_ROLE", "user")


def has_permission(user_id: Optional[str], permission: str) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user_id: User ID
        permission: Permission to check (e.g., "read", "write", "admin")
    
    Returns:
        True if user has permission
    """
    if not RBAC_ENABLED:
        return True  # Allow all when RBAC is disabled
    
    role = get_user_role(user_id)
    user_permissions = ROLES.get(role, [])
    
    return permission in user_permissions


def require_permission(permission: str):
    """
    Decorator to require a specific permission.
    Usage:
        @require_permission("read")
        async def get_job(job_id: str, user_id: Optional[str] = None):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
            
            if not has_permission(user_id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


