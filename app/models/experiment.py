from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class ExperimentVariant(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True

class ExperimentMetrics(BaseModel):
    variant_id: str
    clicks: int = 0
    impressions: int = 0
    conversions: int = 0
    total_revenue: float = 0.0
    avg_session_duration: float = 0.0
    user_satisfaction: float = 0.0
    
    @property
    def ctr(self) -> float:
        """Calculate Click-Through Rate."""
        return self.clicks / self.impressions if self.impressions > 0 else 0
    
    @property
    def conversion_rate(self) -> float:
        """Calculate Conversion Rate."""
        return self.conversions / self.clicks if self.clicks > 0 else 0

class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    variants: List[ExperimentVariant]
    traffic_split: Dict[str, float]

class ExperimentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ExperimentStatus] = None
    variants: Optional[List[ExperimentVariant]] = None
    traffic_split: Optional[Dict[str, float]] = None
    is_active: Optional[bool] = None

class Experiment(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: ExperimentStatus
    variants: List[ExperimentVariant]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: Dict[str, ExperimentMetrics] = {}
    traffic_split: Dict[str, float]
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        from_attributes = True

class UserAssignment(BaseModel):
    user_id: str
    experiment_id: str
    variant_id: str
    assigned_at: datetime = datetime.utcnow()

class ExperimentEvent(BaseModel):
    user_id: str
    experiment_id: str
    variant_id: str
    event_type: str  # e.g., "impression", "click", "conversion"
    metadata: Dict[str, Any] = {}
    timestamp: datetime = datetime.utcnow() 