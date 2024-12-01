from typing import List, Optional, Set
from app.models.rbac import (
    Permission,
    Role,
    RoleDefinition,
    UserRole,
    ROLE_DEFINITIONS
)
from app.models.user import User
from app.db.database import mongodb
from app.core.monitoring import logger, metrics_logger
from fastapi import HTTPException

class RBACService:
    def __init__(self):
        self.user_roles = mongodb.user_roles
        self._role_cache = {}

    async def assign_role(self, user_id: str, role: Role, assigned_by: str) -> UserRole:
        """Assign a role to a user."""
        try:
            # Check if role exists
            if role not in ROLE_DEFINITIONS:
                raise ValueError(f"Invalid role: {role}")
            
            # Create role assignment
            user_role = UserRole(
                user_id=user_id,
                role=role,
                assigned_by=assigned_by
            )
            
            # Store in database
            await self.user_roles.update_one(
                {"user_id": user_id},
                {"$set": user_role.dict()},
                upsert=True
            )
            
            # Clear cache
            if user_id in self._role_cache:
                del self._role_cache[user_id]
            
            logger.info(
                "role_assigned",
                user_id=user_id,
                role=role,
                assigned_by=assigned_by
            )
            
            return user_role
            
        except Exception as e:
            metrics_logger.log_error(
                "role_assignment_error",
                str(e),
                {"user_id": user_id, "role": role}
            )
            raise

    async def get_user_role(self, user_id: str) -> Optional[Role]:
        """Get a user's role."""
        try:
            # Check cache
            if user_id in self._role_cache:
                return self._role_cache[user_id]
            
            # Get from database
            user_role = await self.user_roles.find_one({"user_id": user_id})
            if user_role:
                role = user_role["role"]
                self._role_cache[user_id] = role
                return role
            
            # Default to basic user if no role assigned
            return Role.BASIC_USER
            
        except Exception as e:
            metrics_logger.log_error(
                "get_role_error",
                str(e),
                {"user_id": user_id}
            )
            return Role.BASIC_USER

    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user based on their role."""
        try:
            role = await self.get_user_role(user_id)
            if role not in ROLE_DEFINITIONS:
                return set()
            
            permissions = ROLE_DEFINITIONS[role].permissions
            
            # Add permissions from parent roles
            current_role = ROLE_DEFINITIONS[role]
            while current_role.parent_role:
                parent_role = ROLE_DEFINITIONS[current_role.parent_role]
                permissions.update(parent_role.permissions)
                current_role = parent_role
            
            return permissions
            
        except Exception as e:
            metrics_logger.log_error(
                "get_permissions_error",
                str(e),
                {"user_id": user_id}
            )
            return set()

    async def check_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """Check if a user has a specific permission."""
        try:
            permissions = await self.get_user_permissions(user_id)
            return permission in permissions
        except Exception as e:
            metrics_logger.log_error(
                "check_permission_error",
                str(e),
                {"user_id": user_id, "permission": permission}
            )
            return False

    def require_permission(self, permission: Permission):
        """Decorator to require a specific permission for an endpoint."""
        async def permission_dependency(current_user: User) -> User:
            has_permission = await self.check_permission(
                current_user.id,
                permission
            )
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
            return current_user
        return permission_dependency

    async def get_roles(self) -> List[RoleDefinition]:
        """Get all available roles and their definitions."""
        return list(ROLE_DEFINITIONS.values())

    async def remove_role(self, user_id: str, removed_by: str):
        """Remove a user's role assignment."""
        try:
            await self.user_roles.delete_one({"user_id": user_id})
            
            # Clear cache
            if user_id in self._role_cache:
                del self._role_cache[user_id]
            
            logger.info(
                "role_removed",
                user_id=user_id,
                removed_by=removed_by
            )
            
        except Exception as e:
            metrics_logger.log_error(
                "remove_role_error",
                str(e),
                {"user_id": user_id}
            )
            raise

# Global RBAC service instance
rbac_service = RBACService() 