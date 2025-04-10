from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from redis import Redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# PostgreSQL setup with connection pooling optimized for free tier
try:
    # Configure engine with pool size and timeouts
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        # Echo SQL in debug mode
        echo=(settings.LOG_LEVEL == "DEBUG")
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    logger.info(f"Successfully connected to PostgreSQL with pool_size={settings.DB_POOL_SIZE}")
except Exception as e:
    logger.error(f"PostgreSQL connection error: {str(e)}")
    raise

# MongoDB setup with optimized connection pool
mongodb = None
mongo_client = None
try:
    if settings.MONGODB_URI:
        # Configure MongoDB client with optimized settings
        mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=settings.MONGODB_POOL_SIZE,
            connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS,
            # Enable resource-friendly retry mechanism
            retryWrites=True,
            retryReads=True,
            # Free tier optimizations
            appname="ai-recommendation-api",
            maxIdleTimeMS=30000  # 30 seconds
        )
        mongodb = mongo_client[settings.MONGODB_DB_NAME]
        logger.info(f"Successfully connected to MongoDB with pool_size={settings.MONGODB_POOL_SIZE}")
    else:
        logger.warning("MongoDB connection not configured")
except Exception as e:
    logger.error(f"MongoDB connection error: {str(e)}")

# Redis setup with connection pooling
redis_client = None
try:
    # Check if we have a Redis URL or separate config
    if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
        # Connect using URL with optimized connection pool
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            health_check_interval=30
        )
        logger.info(f"Connected to Redis using URL with max_connections={settings.REDIS_MAX_CONNECTIONS}")
    elif hasattr(settings, 'REDIS_HOST') and settings.REDIS_HOST:
        # Connect using individual parameters with optimized connection pool
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=getattr(settings, 'REDIS_PORT', 6379),
            password=getattr(settings, 'REDIS_PASSWORD', None),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True,
            socket_timeout=settings.REDIS_TIMEOUT,
            socket_connect_timeout=settings.REDIS_TIMEOUT,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            health_check_interval=30
        )
        logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{getattr(settings, 'REDIS_PORT', 6379)} with max_connections={settings.REDIS_MAX_CONNECTIONS}")
    else:
        logger.warning("Redis connection not configured. Some features may be limited.")
    
    # Test connection if client was created
    if redis_client:
        redis_client.ping()
except Exception as e:
    logger.error(f"Redis connection error: {str(e)}")
    redis_client = None  # Ensure it's None if connection failed

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