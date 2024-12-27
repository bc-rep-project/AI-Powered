from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import motor.motor_asyncio
import os
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str = "6543"
    DB_NAME: str

    class Config:
        env_file = ".env"

settings = Settings()

DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Get MongoDB credentials from environment
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set")

try:
    # Create MongoDB client
    mongodb = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = mongodb.recommendation_engine  # Use specific database name
    
    # Test connection immediately
    mongodb.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection failed: {str(e)}")
    raise

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def test_database_connection():
    try:
        # Verify connection
        await mongodb.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False