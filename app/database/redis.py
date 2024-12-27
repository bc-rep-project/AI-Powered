import redis
from ..core.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RedisConnection:
    client: Optional[redis.Redis] = None

    def connect_to_redis(self) -> bool:
        """Connect to Redis with configuration from settings"""
        try:
            # Skip Redis connection if host is not configured
            if not settings.REDIS_HOST:
                logger.info("Redis host not configured, skipping connection")
                return False

            # Use default values for optional settings
            port = getattr(settings, 'REDIS_PORT', 6379)
            db = getattr(settings, 'REDIS_DB', 0)
            password = getattr(settings, 'REDIS_PASSWORD', None)

            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Successfully connected to Redis at {settings.REDIS_HOST}:{port}")
            return True
            
        except Exception as e:
            logger.warning(f"Redis connection error: {str(e)}")
            return False

    def close_redis_connection(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")

redis_client = RedisConnection() 