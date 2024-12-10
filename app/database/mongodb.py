from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
import certifi
from urllib.parse import urlparse

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
            
            # Parse database name from URL
            # If not in URL, use default name
            parsed_url = urlparse(mongodb_url)
            db_name = parsed_url.path.lstrip('/')
            if not db_name or db_name == '':
                db_name = 'recommendation_engine'  # Default database name
            
            # Get database
            self.db = self.client[db_name]
            
            # Test connection
            await self.db.command('ping')
            print(f"Successfully connected to MongoDB database: {db_name}")
            return True
            
        except Exception as e:
            print(f"MongoDB connection error: {str(e)}")
            return False

    async def close_mongodb_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

mongodb = MongoDBConnection()