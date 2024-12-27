from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import certifi
from urllib.parse import urlparse
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDBConnection:
    client: AsyncIOMotorClient = None
    db = None

    async def connect_to_mongodb(self):
        """Connect to MongoDB with proper SSL configuration"""
        try:
            if not settings.MONGODB_URI:
                logger.error("MONGODB_URI not set in environment variables")
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
            
            # Get database using configured name
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await self.db.command('ping')
            logger.info(f"Successfully connected to MongoDB database: {settings.MONGODB_DB_NAME}")
            return True
            
        except Exception as e:
            logger.error(f"MongoDB connection error: {str(e)}")
            return False

    async def close_mongodb_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

mongodb = MongoDBConnection()