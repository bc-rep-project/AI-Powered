import redis
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisConnection:
    client = None

    def connect_to_redis(self):
        """Connect to Redis with configuration from settings"""
        try:
            if not settings.REDIS_HOST:
                logger.error("REDIS_HOST not set in environment variables")
                return False

            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Successfully connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            return True
            
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
            return False

    def close_redis_connection(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")

redis_client = RedisConnection() 