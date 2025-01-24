from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models.user import User
import tensorflow as tf
import numpy as np
import logging

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)

# Load trained model
model = tf.keras.models.load_model(settings.MODEL_SAVE_PATH)

async def get_user_embedding(user_id: str):
    # Get user features from MongoDB
    user_data = await mongodb.users.find_one({"user_id": user_id})
    return np.array(user_data["embedding"])

@router.get("/")
async def get_recommendations(
    user: dict = Depends(get_current_user),
    limit: int = 10
):
    try:
        # Get user embedding
        user_embedding = await get_user_embedding(user["id"])
        
        # Get candidate items from Redis
        content_ids = await redis_client.zrevrange(
            f"user:{user['id']}:recommendations",
            0, limit
        )
        
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
        
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations") 