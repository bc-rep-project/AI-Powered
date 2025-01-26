from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime
from pydantic import field_validator

from ..db.database import Base

class UserInDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    picture = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserBase(BaseModel):
    email: EmailStr
    username: str
    picture: Optional[str] = None
    oauth_provider: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str

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
    is_active: bool = True
    created_at: datetime
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