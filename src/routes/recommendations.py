from fastapi import APIRouter, Depends, HTTPException
from src.models.user import User
from src.auth.jwt import get_current_user
from src.ml.training import RecommenderModel
from src.cache.redis_cache import get_cached_recommendations, cache_recommendations

router = APIRouter()
recommender = RecommenderModel()

@router.get("/recommendations")
async def get_recommendations(current_user: User = Depends(get_current_user)):
    try:
        # First check cache
        cached_recommendations = await get_cached_recommendations(current_user.email)
        if cached_recommendations:
            return cached_recommendations
        
        # If not in cache, generate new recommendations
        recommendations = recommender.predict(current_user.email)
        
        # Cache the new recommendations
        await cache_recommendations(current_user.email, recommendations)
        
        return {
            "user": current_user.email,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )