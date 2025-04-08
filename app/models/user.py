from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import field_validator
import uuid

from ..db.database import Base

# Database model for user
class UserInDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

class UserBase(BaseModel):
    email: EmailStr
    username: str
    picture: Optional[str] = None
    oauth_provider: Optional[str] = None
    
    class Config:
        orm_mode = True

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator('email')
    def email_to_lower(cls, v):
        return v.lower()
    
    @field_validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "username": "johndoe"
            }
        }

class User(UserBase):
    id: str
    is_active: Optional[bool] = True
    picture: Optional[str] = None
    oauth_provider: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Formerly known as orm_mode

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class PasswordReset(BaseModel):
    token: str
    new_password: str 