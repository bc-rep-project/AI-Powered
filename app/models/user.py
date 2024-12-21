from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, constr
from typing import Optional
from datetime import datetime

from ..db.database import Base

class UserBase(BaseModel):
    email: EmailStr
    username: str
    picture: Optional[str] = None
    oauth_provider: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class User(UserBase):
    id: str
    
    class Config:
        from_attributes = True  # Formerly known as orm_mode

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class PasswordReset(BaseModel):
    token: str
    new_password: str 