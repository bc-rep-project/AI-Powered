from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from ..database import Base

# Database model for user profiles
class UserProfileDB(Base):
    __tablename__ = "user_profiles"
    
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    preferences = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

# Pydantic models
class UserProfileBase(BaseModel):
    preferences: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class UserProfileCreate(UserProfileBase):
    pass

class UserProfile(UserProfileBase):
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserProfileUpdate(BaseModel):
    preferences: Optional[Dict[str, Any]] = None 