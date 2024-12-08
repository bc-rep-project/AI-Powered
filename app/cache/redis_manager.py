import redis
from app.core.config import settings
from redis import ConnectionPool
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=10,
                decode_responses=True
            )
        return cls._pool

    @classmethod
    def get_client(cls):
        return redis.Redis(connection_pool=cls.get_pool())

def test_redis_connection():
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        print("Successfully connected to Redis")
        return True
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {str(e)}")
        return False 

def handle_redis_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
            raise
        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            raise
    return wrapper

class CacheService:
    def __init__(self):
        self.redis = RedisManager.get_client()
    
    @handle_redis_errors
    async def cache_recommendations(self, user_id: int, recommendations: list):
        key = f"recommendations:{user_id}"
        await self.redis.setex(
            key,
            timedelta(hours=24),
            json.dumps(recommendations)
        ) 