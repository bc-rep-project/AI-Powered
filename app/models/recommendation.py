from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class UserProfile(BaseModel):
    user_id: str
    preferences: dict = Field(default_factory=dict)
    interaction_history: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ContentItem(BaseModel):
    content_id: str
    title: str
    description: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserInteraction(BaseModel):
    user_id: str
    content_id: str
    interaction_type: str  # e.g., "view", "like", "purchase"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: dict = Field(default_factory=dict)

class Recommendation(BaseModel):
    user_id: str
    content_items: List[ContentItem]
    score: float
    explanation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow) 