from motor.motor_asyncio import AsyncIOMotorClient
from src.config import settings
import logging

logger = logging.getLogger(__name__)

async def get_db():
    try:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = client.recommendation_db
        logger.info("Connected to database: recommendation_db")
        return db
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise