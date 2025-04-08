from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Float
from sqlalchemy.sql import func
from ..database import Base
import enum
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

class ContentType(str, enum.Enum):
    ARTICLE = "article"
    VIDEO = "video"
    PRODUCT = "product"

class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    content_type = Column(Enum(ContentType), nullable=False)
    url = Column(String(512))
    metadata = Column(Text)  # JSON field for flexible metadata
    embedding = Column(Text)  # Store content embedding for similarity search
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Fields for product-specific content
    price = Column(Float)
    category = Column(String(100))
    
    # Fields for video/article-specific content
    author = Column(String(255))
    publication_date = Column(DateTime)
    read_time = Column(Integer)  # in minutes 

# Database model for content items
class ContentItemDB(Base):
    __tablename__ = "content_items"
    
    content_id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String, nullable=False)
    content_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

# Pydantic models
class ContentItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    content_type: str
    
    class Config:
        from_attributes = True

class ContentItemCreate(ContentItemBase):
    content_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ContentItem(ContentItemBase):
    content_id: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ContentItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 