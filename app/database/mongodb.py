from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import certifi
from urllib.parse import urlparse
from ..core.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDBConnection:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    async def connect_to_mongodb(self) -> bool:
        """Connect to MongoDB with proper SSL configuration"""
        try:
            # Skip MongoDB connection if URI is not configured
            if not settings.MONGODB_URI:
                logger.info("MongoDB URI not configured, skipping connection")
                return False

            # Configure MongoDB client with modern SSL settings
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                server_api=ServerApi('1'),
                tlsCAFile=certifi.where(),
                ssl=True,
                retryWrites=True,
                w="majority"
            )
            
            # Get database using configured name or default
            db_name = getattr(settings, 'MONGODB_DB_NAME', 'ai_recommendation')
            self.db = self.client[db_name]
            
            # Test connection
            await self.db.command('ping')
            logger.info(f"Successfully connected to MongoDB database: {db_name}")
            return True
            
        except Exception as e:
            logger.warning(f"MongoDB connection error: {str(e)}")
            return False

    async def close_mongodb_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

mongodb = MongoDBConnection()