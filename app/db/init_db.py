import logging
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, inspect, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from ..database import Base, get_db
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Define models for direct import from SQLAlchemy
class UserInDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

class InteractionDB(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    content_id = Column(Text, nullable=False)
    interaction_type = Column(Text, nullable=False)
    value = Column(Numeric, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    interaction_metadata = Column(JSONB, nullable=True)

class ContentItemDB(Base):
    __tablename__ = "content_items"
    
    content_id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(String, nullable=False)
    content_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

class UserProfileDB(Base):
    __tablename__ = "user_profiles"
    
    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    preferences = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

async def init_db():
    """Initialize database and create tables"""
    from ..database import engine, Base
    
    try:
        # Create all tables
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            # Check for existing tables
            inspector = inspect(conn)
            existing_tables = inspector.get_table_names()
            
            # Create tables that don't exist
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        return False

def get_table_names():
    """Get list of all tables in the database"""
    from ..database import engine
    
    inspector = inspect(engine)
    return inspector.get_table_names() 