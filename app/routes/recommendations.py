from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any
import logging
import json
import os
import random
from pydantic import BaseModel
from ..db.mongodb import get_mongodb
from ..db.redis import get_redis
from ..services.dataset_manager import get_movie_by_id, search_movies_by_title
from ..core.auth import get_current_user
from ..models.user import UserInDB
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class MovieRecommendation(BaseModel):
    """Movie recommendation model"""
    movie_id: str
    title: str
    year: Optional[int] = None
    genres: List[str] = []
    score: float = 0.0

class RecommendationsResponse(BaseModel):
    """Response model for movie recommendations"""
    recommendations: List[MovieRecommendation]
    strategy: str
    user_id: Optional[str] = None
    total: int

# Constants for model directory
MODELS_DIR = "models"
RECOMMENDER_DIR = os.path.join(MODELS_DIR, "recommender")
MATRIX_FACTORS_FILE = os.path.join(RECOMMENDER_DIR, "matrix_factors.npz")
MODEL_METADATA_FILE = os.path.join(RECOMMENDER_DIR, "model_metadata.json")

# Make sure model directory exists
os.makedirs(RECOMMENDER_DIR, exist_ok=True)

async def load_model_metadata():
    """Load model metadata from file or database"""
    try:
        # Try Redis first
        redis = await get_redis()
        if redis:
            metadata_json = await redis.get("model:metadata")
            if metadata_json:
                return json.loads(metadata_json)
        
        # Fallback to file
        if os.path.exists(MODEL_METADATA_FILE):
            with open(MODEL_METADATA_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading model metadata: {str(e)}")
    
    return None

async def get_popular_movies(limit: int = 10) -> List[MovieRecommendation]:
    """Get popular movies as fallback recommendation strategy"""
    try:
        # Try MongoDB first - aggregate to find most rated movies
        mongodb = await get_mongodb()
        popular_movies = []
        
        if mongodb:
            # Aggregate to find movies with most interactions
            pipeline = [
                {"$group": {
                    "_id": "$content_id", 
                    "count": {"$sum": 1},
                    "avg_rating": {"$avg": "$value"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            popular_ids = []
            async for doc in mongodb.interactions.aggregate(pipeline):
                popular_ids.append({
                    "movie_id": doc["_id"],
                    "score": float(doc["avg_rating"]),
                    "count": doc["count"]
                })
            
            # Get movie details for each popular movie
            for item in popular_ids:
                movie = await get_movie_by_id(item["movie_id"])
                if movie:
                    popular_movies.append(MovieRecommendation(
                        movie_id=movie["movie_id"],
                        title=movie["title"],
                        year=movie.get("year"),
                        genres=movie.get("genres", []),
                        score=item["score"]
                    ))
            
            if popular_movies:
                return popular_movies
        
        # Fallback to Redis cache
        redis = await get_redis()
        if redis:
            cache_key = "popular_movies"
            cached = await redis.get(cache_key)
            if cached:
                return [MovieRecommendation(**movie) for movie in json.loads(cached)]
        
        # Final fallback - return random movies from search
        random_titles = ["star", "love", "war", "adventure", "world", "house", "life"]
        random_title = random.choice(random_titles)
        random_movies = await search_movies_by_title(random_title, limit=limit)
        
        return [MovieRecommendation(
            movie_id=movie["movie_id"],
            title=movie["title"],
            year=movie.get("year"),
            genres=movie.get("genres", []),
            score=random.uniform(3.5, 4.8)  # Random score between 3.5-4.8
        ) for movie in random_movies]
        
    except Exception as e:
        logger.error(f"Error getting popular movies: {str(e)}")
        # Return empty list if all fails
        return []

@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    limit: int = Query(10, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get personalized movie recommendations for the current user.
    If the user has no interactions, returns popular recommendations.
    """
    user_id = str(current_user.id)
    recommendation_strategy = "personalized"
    
    try:
        # First check if we have model files available
        try:
            model_metadata = await load_model_metadata()
            model_available = model_metadata and os.path.exists(getattr(settings, 'MODEL_PATH', 'models/latest'))
        except Exception as model_err:
            logger.warning(f"Could not load model metadata: {str(model_err)}")
            model_available = False
        
        # Get user interactions from MongoDB
        mongodb = await get_mongodb()
        user_interactions = []
        
        if mongodb:
            try:
                cursor = mongodb.interactions.find({"user_id": user_id}).sort("timestamp", -1)
                async for interaction in cursor:
                    user_interactions.append(interaction)
            except Exception as db_err:
                logger.warning(f"Error retrieving user interactions: {str(db_err)}")
        
        recommendations = []
        
        # If user has interactions and model exists, generate personalized recommendations
        if user_interactions and model_available:
            try:
                # Cache recommendations in Redis for 1 hour to avoid repeated computation
                redis = await get_redis()
                cache_key = f"user_recommendations:{user_id}"
                
                if redis:
                    try:
                        cached = await redis.get(cache_key)
                        if cached:
                            recommendations = [MovieRecommendation(**movie) for movie in json.loads(cached)]
                    except Exception as redis_err:
                        logger.warning(f"Redis cache error: {str(redis_err)}")
                
                # If no cache and model is available, load model and generate recommendations
                if not recommendations and model_available:
                    # Here would be model-based recommendations code
                    # For now, we'll fall back to popularity-based recommendations
                    logger.info("Falling back to popularity-based recommendations")
                    recommendation_strategy = "popular_fallback"
            except Exception as rec_err:
                logger.error(f"Error generating personalized recommendations: {str(rec_err)}")
                recommendation_strategy = "model_error"
        else:
            if not user_interactions:
                recommendation_strategy = "new_user"
            else:
                recommendation_strategy = "model_unavailable"
                
        # Fallback to popularity-based if:
        # - User has no interactions
        # - Model doesn't exist
        # - Error in generating personalized recommendations
        if not recommendations:
            recommendations = await get_popular_movies(limit=limit)
            
        # Ensure we don't exceed the limit
        recommendations = recommendations[:limit]
        
        return RecommendationsResponse(
            recommendations=recommendations,
            strategy=recommendation_strategy,
            user_id=user_id,
            total=len(recommendations)
        )
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        # Even on error, try to return something rather than a 500 error
        try:
            popular_recs = await get_popular_movies(limit=limit)
            return RecommendationsResponse(
                recommendations=popular_recs,
                strategy="error_fallback",
                user_id=user_id,
                total=len(popular_recs)
            )
        except Exception:
            # If even that fails, raise the HTTP exception
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating recommendations: {str(e)}"
            )