from pydantic_settings import BaseSettings
import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Determine database URL
try:
    # Try to create database URL from environment variables
    if settings.DATABASE_URL:
        DATABASE_URL = settings.DATABASE_URL
    elif all([settings.DB_USER, settings.DB_HOST, settings.DB_PORT, settings.DB_NAME]):
        # If necessary components are available, construct the URL
        DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    else:
        # Fall back to SQLite for development or when PostgreSQL is unavailable
        logger.warning("PostgreSQL connection info incomplete. Using SQLite instead.")
        DATABASE_URL = "sqlite:///./app.db"
except Exception as e:
    logger.warning(f"Error configuring PostgreSQL: {str(e)}. Using SQLite instead.")
    DATABASE_URL = "sqlite:///./app.db"

# Create engine with appropriate parameters based on database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    logger.info("Using SQLite database")
else:
    engine = create_engine(DATABASE_URL)
    logger.info("Using PostgreSQL database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Define a basic User model for SQLite fallback
class UserInDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

# Initialize database function
def init_db():
    """Initialize database and create tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        return False

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_database_connection():
    """Test the database connection by executing a simple query"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return False 