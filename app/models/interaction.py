from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, ForeignKey
from sqlalchemy.sql import func
from ..database import Base
import enum

class InteractionType(str, enum.Enum):
    VIEW = "view"
    LIKE = "like"
    BOOKMARK = "bookmark"
    PURCHASE = "purchase"
    SHARE = "share"
    COMMENT = "comment"
    TIME_SPENT = "time_spent"

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    interaction_type = Column(Enum(InteractionType), nullable=False)
    
    # Interaction metadata
    value = Column(Float)  # For storing ratings or time spent
    metadata = Column(String)  # JSON field for additional interaction data
    
    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Context of the interaction
    session_id = Column(String)
    user_agent = Column(String)
    referrer = Column(String) 