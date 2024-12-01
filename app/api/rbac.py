from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.rbac import (
    Role,
    RoleDefinition,
    UserRole,
    RoleAssignment,
    Permission
)
from app.models.user import User
from app.core.auth import get_current_user
from app.services.rbac_service import rbac_service
from app.core.monitoring import monitor_endpoint, metrics_logger

router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])

@router.get("/roles", response_model=List[RoleDefinition])
@monitor_endpoint("get_roles")
async def get_roles(
    current_user: User = Depends(
        rbac_service.require_permission(Permission.VIEW_USERS)
    )
):
    """Get all available roles and their definitions."""
    try:
        return await rbac_service.get_roles()
    except Exception as e:
        metrics_logger.log_error("get_roles_error", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/roles/assign", response_model=UserRole)
@monitor_endpoint("assign_role")
async def assign_role(
    assignment: RoleAssignment,
    current_user: User = Depends(
        rbac_service.require_permission(Permission.MANAGE_USERS)
    )
):
    """Assign a role to a user."""
    try:
        return await rbac_service.assign_role(
            assignment.user_id,
            assignment.role,
            current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        metrics_logger.log_error(
            "assign_role_error",
            str(e),
            {"assignment": assignment.dict()}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/roles/{user_id}")
@monitor_endpoint("remove_role")
async def remove_role(
    user_id: str,
    current_user: User = Depends(
        rbac_service.require_permission(Permission.MANAGE_USERS)
    )
):
    """Remove a user's role assignment."""
    try:
        await rbac_service.remove_role(user_id, current_user.id)
        return {"status": "success", "message": "Role removed"}
    except Exception as e:
        metrics_logger.log_error(
            "remove_role_error",
            str(e),
            {"user_id": user_id}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/role", response_model=Role)
@monitor_endpoint("get_user_role")
async def get_user_role(
    user_id: str,
    current_user: User = Depends(
        rbac_service.require_permission(Permission.VIEW_USERS)
    )
):
    """Get a user's current role."""
    try:
        role = await rbac_service.get_user_role(user_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except HTTPException:
        raise
    except Exception as e:
        metrics_logger.log_error(
            "get_user_role_error",
            str(e),
            {"user_id": user_id}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/permissions", response_model=List[Permission])
@monitor_endpoint("get_user_permissions")
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(
        rbac_service.require_permission(Permission.VIEW_USERS)
    )
):
    """Get all permissions for a user."""
    try:
        permissions = await rbac_service.get_user_permissions(user_id)
        return list(permissions)
    except Exception as e:
        metrics_logger.log_error(
            "get_user_permissions_error",
            str(e),
            {"user_id": user_id}
        )
        raise HTTPException(status_code=500, detail=str(e)) 