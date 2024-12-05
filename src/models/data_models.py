from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid

class Content(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    type: str  # article, video, product, etc.
    metadata: Dict
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []
    
class Interaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_id: str
    interaction_type: str  # view, click, like, share, purchase
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = {}
    
class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: Optional[str]
    preferences: Dict = {}
    interaction_history: List[str] = []  # List of interaction IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    
class RecommendationHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_ids: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    algorithm_version: str
    scores: List[float]
    feedback: Optional[Dict] = None 