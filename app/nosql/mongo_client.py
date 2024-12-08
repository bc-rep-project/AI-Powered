from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client.recommendation_engine

async def store_interaction(interaction: UserInteraction):
    await db.interactions.insert_one(interaction.dict()) 