from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel
from datetime import datetime

class Permission(str, Enum):
    # User management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    
    # Content management
    MANAGE_CONTENT = "manage_content"
    VIEW_CONTENT = "view_content"
    
    # Recommendation management
    MANAGE_RECOMMENDATIONS = "manage_recommendations"
    VIEW_RECOMMENDATIONS = "view_recommendations"
    
    # Experiment management
    MANAGE_EXPERIMENTS = "manage_experiments"
    VIEW_EXPERIMENTS = "view_experiments"
    RUN_EXPERIMENTS = "run_experiments"
    
    # System management
    VIEW_METRICS = "view_metrics"
    MANAGE_SYSTEM = "manage_system"
    VIEW_LOGS = "view_logs"
    
    # Model management
    TRAIN_MODELS = "train_models"
    VIEW_MODELS = "view_models"

class Role(str, Enum):
    ADMIN = "admin"
    CONTENT_MANAGER = "content_manager"
    EXPERIMENTER = "experimenter"
    ANALYST = "analyst"
    BASIC_USER = "basic_user"

class RoleDefinition(BaseModel):
    name: Role
    description: str
    permissions: Set[Permission]
    parent_role: Optional[Role] = None

# Define role hierarchy and permissions
ROLE_DEFINITIONS = {
    Role.ADMIN: RoleDefinition(
        name=Role.ADMIN,
        description="Full system access",
        permissions=set(Permission),
        parent_role=None
    ),
    Role.CONTENT_MANAGER: RoleDefinition(
        name=Role.CONTENT_MANAGER,
        description="Manage content and view recommendations",
        permissions={
            Permission.MANAGE_CONTENT,
            Permission.VIEW_CONTENT,
            Permission.VIEW_RECOMMENDATIONS,
            Permission.VIEW_METRICS
        },
        parent_role=None
    ),
    Role.EXPERIMENTER: RoleDefinition(
        name=Role.EXPERIMENTER,
        description="Manage and run experiments",
        permissions={
            Permission.MANAGE_EXPERIMENTS,
            Permission.VIEW_EXPERIMENTS,
            Permission.RUN_EXPERIMENTS,
            Permission.VIEW_METRICS,
            Permission.VIEW_CONTENT,
            Permission.VIEW_RECOMMENDATIONS
        },
        parent_role=None
    ),
    Role.ANALYST: RoleDefinition(
        name=Role.ANALYST,
        description="View and analyze system data",
        permissions={
            Permission.VIEW_METRICS,
            Permission.VIEW_LOGS,
            Permission.VIEW_EXPERIMENTS,
            Permission.VIEW_CONTENT,
            Permission.VIEW_RECOMMENDATIONS,
            Permission.VIEW_MODELS
        },
        parent_role=None
    ),
    Role.BASIC_USER: RoleDefinition(
        name=Role.BASIC_USER,
        description="Basic user access",
        permissions={
            Permission.VIEW_CONTENT,
            Permission.VIEW_RECOMMENDATIONS
        },
        parent_role=None
    )
}

class UserRole(BaseModel):
    user_id: str
    role: Role
    assigned_at: datetime = datetime.utcnow()
    assigned_by: Optional[str] = None

class RoleAssignment(BaseModel):
    user_id: str
    role: Role
    assigned_by: str

class PermissionCheck(BaseModel):
    user_id: str
    permission: Permission 