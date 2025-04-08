"""
Interaction counter service for tracking user interactions for model retraining.
"""

import logging
from typing import Optional
from ..db.redis import get_redis

logger = logging.getLogger(__name__)

async def increment_interaction_counter() -> bool:
    """
    Increment the counter for new interactions since last model retraining.
    This should be called every time a user interacts with content.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        redis = await get_redis()
        if redis:
            # Get current count (default to 0 if not exists)
            current_count = await redis.get("new_interactions_count")
            if current_count is None:
                await redis.set("new_interactions_count", 1)
            else:
                await redis.incr("new_interactions_count")
            return True
        else:
            logger.warning("Redis not available. Interaction count not incremented.")
            return False
    except Exception as e:
        logger.error(f"Error incrementing interaction counter: {str(e)}")
        return False

async def get_interaction_count() -> Optional[int]:
    """
    Get the current count of new interactions since last model retraining.
    
    Returns:
        Optional[int]: The count of new interactions, or None if error
    """
    try:
        redis = await get_redis()
        if redis:
            count = await redis.get("new_interactions_count")
            return int(count) if count is not None else 0
        else:
            logger.warning("Redis not available. Cannot get interaction count.")
            return None
    except Exception as e:
        logger.error(f"Error getting interaction count: {str(e)}")
        return None

async def reset_interaction_counter() -> bool:
    """
    Reset the interaction counter to zero.
    This should be called after model retraining.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        redis = await get_redis()
        if redis:
            await redis.set("new_interactions_count", 0)
            return True
        else:
            logger.warning("Redis not available. Interaction count not reset.")
            return False
    except Exception as e:
        logger.error(f"Error resetting interaction counter: {str(e)}")
        return False

