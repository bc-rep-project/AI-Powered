from redis import Redis
import json
from src.config import settings

redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

CACHE_TTL = 3600  # 1 hour

async def cache_recommendations(user_id: str, recommendations: list):
    try:
        key = f"recommendations:{user_id}"
        redis_client.setex(
            key,
            CACHE_TTL,
            json.dumps(recommendations)
        )
        return True
    except Exception as e:
        print(f"Cache error: {str(e)}")
        return False

async def get_cached_recommendations(user_id: str):
    try:
        key = f"recommendations:{user_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Cache error: {str(e)}")
        return None 