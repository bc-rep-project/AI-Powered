from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import certifi

class MongoDBConnection:
    client: AsyncIOMotorClient = None
    db = None

    async def connect_to_mongodb(self, mongodb_url: str):
        """Connect to MongoDB with proper SSL configuration"""
        try:
            # Configure MongoDB client with modern SSL settings
            self.client = AsyncIOMotorClient(
                mongodb_url,
                server_api=ServerApi('1'),
                tlsCAFile=certifi.where(),
                ssl=True,
                retryWrites=True,
                w="majority"
            )
            
            # Get database from connection string
            db_name = mongodb_url.split('/')[-1].split('?')[0]
            self.db = self.client[db_name]
            
            # Test connection
            await self.db.command('ping')
            return True
            
        except Exception as e:
            print(f"MongoDB connection error: {str(e)}")
            return False

    async def close_mongodb_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

mongodb = MongoDBConnection() 