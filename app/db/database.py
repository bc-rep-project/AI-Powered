from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL setup
try:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info("Successfully connected to PostgreSQL")
except Exception as e:
    logger.error(f"PostgreSQL connection error: {str(e)}")
    raise

# MongoDB setup
try:
    if settings.MONGODB_URI:
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        mongodb = mongo_client.get_database()
        logger.info("Successfully connected to MongoDB")
    else:
        logger.warning("MONGODB_URI not configured")
        mongodb = None
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")
    mongodb = None

# Redis setup
try:
    redis_client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Successfully connected to Redis")
except Exception as e:
    logger.error(f"Redis connection error: {str(e)}")
    redis_client = None

# Database dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# MongoDB collections
if mongodb:
    user_interactions = mongodb.user_interactions
    content_items = mongodb.content_items
    user_profiles = mongodb.user_profiles