from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None
    
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DB_NAME]
            logger.info("Connected to MongoDB.")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise
    
    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")
    
    def get_db(self):
        if not self.db:
            raise Exception("Database not initialized")
        return self.db

mongodb = MongoDB()

async def get_mongodb():
    if not mongodb.client:
        await mongodb.connect()
    return mongodb.db