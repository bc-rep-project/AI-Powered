from redis import asyncio as aioredis
from ..core.config import settings

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    encoding="utf-8"
)

async def get_redis():
    return redis_client