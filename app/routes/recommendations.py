from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from app.models.user import User
from app.core.config import settings
from app.db.mongodb import get_mongodb
import tensorflow as tf
import numpy as np
import logging
from redis import asyncio as aioredis
from tensorflow.keras.layers import TFSMLayer

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True
)

# Initialize MongoDB client
mongodb = get_mongodb()

# Load trained model
try:
    # Load model as inference-only layer
    model = TFSMLayer(
        settings.MODEL_SAVE_PATH,
        call_endpoint='serving_default'
    )
    logger.info("Loaded TensorFlow SavedModel as TFSMLayer")
except Exception as e:
    logger.warning(f"Could not load model: {str(e)}")
    model = None

async def get_user_embedding(user_id: str):
    try:
        # Get user features from MongoDB
        user_data = await mongodb.users.find_one({"user_id": user_id})
        if not user_data or "embedding" not in user_data:
            raise HTTPException(
                status_code=404,
                detail="User embedding not found"
            )
        return np.array(user_data["embedding"])
    except Exception as e:
        logger.error(f"Error getting user embedding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user embedding"
        )

@router.get("/", dependencies=[Depends(get_current_user)])
async def get_recommendations(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    try:
        if model is None:
            # Return fallback recommendations if model isn't loaded
            fallback_recs = await get_fallback_recommendations(user["id"], limit)
            return {
                "user_id": user["id"],
                "recommendations": fallback_recs,
                "message": "Using fallback recommendations"
            }

        # Get user embedding
        user_embedding = await get_user_embedding(user["id"])
        
        # Get candidate items from Redis
        content_ids = await redis_client.zrevrange(
            f"user:{user['id']}:recommendations",
            0, limit
        )
        
        if not content_ids:
            # If no recommendations in Redis, get fallback
            content_ids = await get_fallback_content_ids(limit)
        
        # Generate predictions
        predictions = model.predict([np.array([user_embedding]*len(content_ids)), 
                                   np.array(content_ids)])
        
        # Format results
        recommendations = sorted(zip(content_ids, predictions), 
                                key=lambda x: x[1], reverse=True)
        
        return {
            "user_id": user["id"],
            "recommendations": [
                {"content_id": cid, "score": float(score)}
                for cid, score in recommendations
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

async def get_fallback_recommendations(user_id: str, limit: int = 10):
    try:
        # Get most recent or popular content
        cursor = mongodb.content.find(
            {"status": "active"},
            sort=[("popularity", -1)],
            limit=limit
        )
        content = await cursor.to_list(length=limit)
        
        return [
            {
                "content_id": str(item["_id"]),
                "score": 0.5  # Default score for fallback recommendations
            }
            for item in content
        ]
    except Exception as e:
        logger.error(f"Error getting fallback recommendations: {str(e)}")
        return []

async def get_fallback_content_ids(limit: int = 10):
    try:
        cursor = mongodb.content.find(
            {"status": "active"},
            sort=[("created_at", -1)],
            limit=limit
        )
        content = await cursor.to_list(length=limit)
        return [str(item["_id"]) for item in content]
    except Exception as e:
        logger.error(f"Error getting fallback content IDs: {str(e)}")
        return [] 