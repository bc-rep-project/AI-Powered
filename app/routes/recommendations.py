from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
import json
import sys
import numpy as np
from datetime import datetime
from app.core.auth import get_current_user
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.interaction import InteractionDB
from app.core.config import settings
from app.db.mongodb import mongodb
import random
import tensorflow as tf

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# Path to models and data
MODELS_PATH = os.environ.get("MODEL_PATH", "models/latest")
CONTENT_PATH = os.environ.get("CONTENT_PATH", "data/processed/movielens-small")

# Models for responses
class RecommendationItem(BaseModel):
    content_id: str
    title: str
    description: Optional[str] = None
    genres: List[str] = []
    year: Optional[int] = None
    score: float

class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[RecommendationItem]
    model_version: Optional[str] = None
    timestamp: str = datetime.now().isoformat()
    message: Optional[str] = None

# Global model variable
recommendation_model = None

# Global variable for caching the model
_model = None

# Global variable for caching content items
_content_items = None
_content_items_last_loaded = None

# Function to load the model
def load_model():
    """Load the TensorFlow recommendation model."""
    model_path = os.path.join(os.getcwd(), settings.MODEL_PATH)
    if not os.path.exists(model_path):
        logger.warning(f"Model path {model_path} does not exist.")
        return None
    
    try:
        logger.info(f"Loading model from {model_path}")
        model = tf.saved_model.load(model_path)
        return model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None

# Function to load content items
def get_content_items():
    """Get content items from file or MongoDB."""
    global _content_items, _content_items_last_loaded
    
    # Try to get from MongoDB first if available
    if mongodb is not None:
        try:
            # If the collection exists and has data, return it
            if hasattr(mongodb, 'content_items'):
                count = mongodb.content_items.count_documents({})
                if count > 0:
                    logger.info(f"Getting {count} content items from MongoDB")
                    items = {}
                    cursor = mongodb.content_items.find({})
                    for doc in cursor:
                        items[doc['content_id']] = doc
                    return items
        except Exception as e:
            logger.error(f"Error getting content items from MongoDB: {str(e)}")
    
    # Fallback to file
    content_path = os.path.join(os.getcwd(), settings.CONTENT_PATH, 'content_items.json')
    
    # If path doesn't exist, try getting from data directory
    if not os.path.exists(content_path):
        logger.error(f"Could not find content items file in {settings.CONTENT_PATH}")
        
        # Try alternative paths
        alt_path = os.path.join(os.getcwd(), 'data', 'processed', 'movielens-small', 'content_items.json')
        if os.path.exists(alt_path):
            content_path = alt_path
            logger.info(f"Found content items at alternative path: {alt_path}")
        else:
            # Return empty dict as fallback
            return {}
    
    try:
        with open(content_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading content items: {str(e)}")
        return {}

# Function to get content item by ID
def get_content_item(content_id):
    content_items = get_content_items()
    return content_items.get(content_id)

@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    limit: int = 10,
    genre: Optional[str] = None,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized recommendations for the logged-in user.
    
    If no interactions are found, returns popular items as recommendations.
    """
    global _model
    
    user_id = user.id
    
    # Try to load content items
    content_items = get_content_items()
    if not content_items:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load content items"
        )
    
    # Try to load the model if not already loaded
    if _model is None:
        _model = load_model()
    
    # If we have a model and user interactions, generate personalized recommendations
    if _model is not None:
        try:
            # Get user interactions from MongoDB if available
            user_interactions = []
            if mongodb is not None and hasattr(mongodb, 'user_interactions'):
                interactions_cursor = mongodb.user_interactions.find({"user_id": user_id})
                for doc in interactions_cursor:
                    user_interactions.append(doc)
            
            if user_interactions:
                # Generate recommendations using the model
                logger.info(f"Generating personalized recommendations for user {user_id}")
                
                # This is a simplified example - in a real app you'd use the model API
                try:
                    # Get content IDs the user has interacted with
                    interacted_content_ids = [interaction["content_id"] for interaction in user_interactions]
                    
                    # Get recommendations from model
                    # This is just a placeholder - your model API might be different
                    recommendations = _model.recommend(
                        user_id=user_id,
                        exclude_items=interacted_content_ids,
                        k=limit*2  # Get extra for filtering
                    )
                    
                    # Process recommendations
                    rec_items = []
                    for content_id, score in recommendations:
                        item = get_content_item(content_id)
                        if item:
                            # Apply genre filter if specified
                            if genre and genre not in item.get("genres", []):
                                continue
                                
                            rec_items.append(
                                RecommendationItem(
                                    content_id=content_id,
                                    title=item.get("title", ""),
                                    description=item.get("description", ""),
                                    genres=item.get("genres", []),
                                    year=item.get("year"),
                                    score=float(score)
                                )
                            )
                            
                            if len(rec_items) >= limit:
                                break
                    
                    return RecommendationResponse(
                        user_id=user_id,
                        recommendations=rec_items,
                        model_version=os.path.basename(settings.MODEL_PATH),
                        message="Personalized recommendations based on your history"
                    )
                except Exception as e:
                    logger.error(f"Error generating personalized recommendations: {str(e)}")
                    # Fall through to popularity-based recommendations
            
            # If no user interactions or error, fall back to popularity-based recommendations
            logger.info("Falling back to popularity-based recommendations")
        except Exception as e:
            logger.error(f"Error in recommendation generation: {str(e)}")
            # Fall through to popularity-based recommendations
    
    # Fallback: Get popular items sorted by popularity
    logger.info("Generating popularity-based recommendations")
    
    # Extract all items into a list
    all_items = list(content_items.values())
    
    # Sort by popularity (could be ratings count, views, etc.)
    # This is just an example - your popularity metric might be different
    popular_items = sorted(
        all_items, 
        key=lambda x: x.get("popularity", 0) if isinstance(x.get("popularity"), (int, float)) else 0,
        reverse=True
    )
    
    # Apply genre filter if specified
    if genre:
        popular_items = [item for item in popular_items if genre in item.get("genres", [])]
    
    # Limit number of items
    popular_items = popular_items[:limit]
    
    # If there are still no items, return random items as last resort
    if not popular_items and content_items:
        logger.info("Falling back to random recommendations")
        random_items = random.sample(list(content_items.values()), min(limit, len(content_items)))
        popular_items = random_items
    
    # Create recommendation items
    rec_items = []
    for item in popular_items:
        if isinstance(item, dict):
            rec_items.append(
                RecommendationItem(
                    content_id=item.get("content_id", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    genres=item.get("genres", []),
                    year=item.get("year"),
                    score=float(item.get("popularity", 0)) if isinstance(item.get("popularity"), (int, float)) else 0.0
                )
            )
    
    return RecommendationResponse(
        user_id=user_id,
        recommendations=rec_items,
        message="Popular content recommendations"
    ) 