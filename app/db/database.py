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
mongodb = None
mongo_client = None
try:
    if settings.MONGODB_URI:
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        mongodb = mongo_client[settings.MONGODB_DB_NAME]
        logger.info("Successfully connected to MongoDB")
    else:
        logger.warning("MongoDB connection not configured")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")

# Redis setup
redis_client = None
try:
    redis_client = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Successfully connected to Redis")
except Exception as e:
    logger.error(f"Redis connection error: {str(e)}")

# Database dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# MongoDB collections
user_interactions = None
content_items = None
user_profiles = None

if mongodb is not None:
    user_interactions = mongodb.user_interactions
    content_items = mongodb.content_items
    user_profiles = mongodb.user_profiles

# MongoDB dependency
async def get_mongodb():
    if mongodb is None:
        raise ConnectionError("MongoDB connection not available")
    return mongodb

# Redis dependency
async def get_redis():
    if redis_client is None:
        raise ConnectionError("Redis connection not available")
    return redis_client