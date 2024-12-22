from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
import motor.motor_asyncio
import os
from urllib.parse import quote_plus

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
    await db.command('ping')
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB connection failed: {str(e)}")
    raise

async def test_database_connection():
    try:
        # Verify connection
        await client.admin.command('ping')
        return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

# Example table relationships
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    preferences = Column(JSONB)  # Using JSONB for flexible preference storage