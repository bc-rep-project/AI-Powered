from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class RecommendationBase(BaseModel):
    user_id: int
    content_id: int
    score: float
    category: str
    timestamp: datetime = datetime.now()
    
class RecommendationCreate(RecommendationBase):
    pass

class RecommendationResponse(RecommendationBase):
    id: int
    interaction_count: int
    last_interaction: Optional[datetime]
    
    class Config:
        from_attributes = True 