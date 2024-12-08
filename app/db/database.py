from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis
from app.core.config import settings
import logging

# PostgreSQL setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MongoDB setup
try:
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    mongodb = mongo_client.get_database()
    logging.info("Successfully connected to MongoDB")
except Exception as e:
    logging.error(f"MongoDB connection error: {str(e)}")
    mongodb = None

# Redis setup
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)

# Database dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_mongodb():
    if mongodb is None:
        raise ConnectionError("MongoDB connection not available")
    return mongodb

# MongoDB collections
user_interactions = mongodb.user_interactions
content_items = mongodb.content_items
user_profiles = mongodb.user_profiles 