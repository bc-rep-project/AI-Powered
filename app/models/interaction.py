from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from ..database import Base

# Database model for interactions
class InteractionDB(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    content_id = Column(Text, nullable=False)
    interaction_type = Column(Text, nullable=False)
    value = Column(Numeric, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    metadata = Column(JSONB, nullable=True)

# Pydantic models
class InteractionBase(BaseModel):
    content_id: str
    interaction_type: str
    value: Optional[float] = None
    
    class Config:
        orm_mode = True

class InteractionCreate(InteractionBase):
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Interaction(InteractionBase):
    id: int
    user_id: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class InteractionUpdate(BaseModel):
    value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None 