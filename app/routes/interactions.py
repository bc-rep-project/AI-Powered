from fastapi import APIRouter, Depends, HTTPException
from app.models.interaction import InteractionCreate
from app.core.auth import get_current_user
from datetime import datetime
import logging

router = APIRouter(prefix="/interactions", tags=["interactions"])
logger = logging.getLogger(__name__)

@router.post("/")
async def track_interaction(
    interaction: InteractionCreate,
    user: dict = Depends(get_current_user)
):
    try:
        interaction_data = {
            "user_id": user["id"],
            "content_id": interaction.content_id,
            "type": interaction.type,
            "value": interaction.value,
            "timestamp": datetime.utcnow(),
            "metadata": interaction.metadata
        }
        
        # Store in MongoDB
        result = await mongodb.interactions.insert_one(interaction_data)
        
        # Update Redis for real-time recommendations
        await redis_client.zincrby(
            f"user:{user['id']}:preferences",
            1,
            interaction.content_id
        )
        
        return {"status": "interaction tracked", "id": str(result.inserted_id)}
        
    except Exception as e:
        logger.error(f"Error tracking interaction: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to track interaction") 