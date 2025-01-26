from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
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

DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

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
async def get_db():
    async with SessionLocal() as session:
        yield session

async def test_database_connection():
    try:
        # Verify connection
        await mongodb.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False