from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime

class Content(BaseModel):
    """Content model."""
    id: str
    title: str
    description: str
    type: str
    metadata: Dict
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None

class Interaction(BaseModel):
    """User-content interaction model."""
    user_id: str
    content_id: str
    interaction_type: str
    timestamp: datetime = datetime.utcnow()
    metadata: Optional[Dict] = None

class UserProfile(BaseModel):
    """User profile model."""
    email: EmailStr
    name: Optional[str] = None
    preferences: Optional[Dict] = None
    created_at: datetime = datetime.utcnow()
    updated_at: Optional[datetime] = None

class RecommendationHistory(BaseModel):
    """Recommendation history model."""
    user_id: str
    content_id: str
    score: float
    rank: int
    timestamp: datetime = datetime.utcnow()
    metadata: Optional[Dict] = None 