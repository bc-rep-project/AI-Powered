from fastapi import APIRouter, Depends, HTTPException, status
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

# Function to load the model
def load_model():
    global recommendation_model
    
    try:
        if recommendation_model is not None:
            return recommendation_model
            
        # Import RecommendationModel from train_model.py
        sys.path.append('.')
        try:
            from scripts.train_model import RecommendationModel
        except ImportError:
            try:
                # Try to import from the specific location
                sys.path.append('./scripts')
                from train_model import RecommendationModel
            except ImportError:
                logger.error("Could not import RecommendationModel. Make sure scripts/train_model.py exists.")
                return None
        
        # Check if model path exists
        if not os.path.exists(MODELS_PATH):
            logger.warning(f"Model path {MODELS_PATH} does not exist.")
            return None
            
        # Load the model
        logger.info(f"Loading model from {MODELS_PATH}")
        recommendation_model = RecommendationModel.load(MODELS_PATH)
        logger.info("Model loaded successfully")
        
        return recommendation_model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None

# Function to load content items
def get_content_items():
    try:
        content_path = os.path.join(CONTENT_PATH, 'movies.json')
        if not os.path.exists(content_path):
            # Try alternative paths
            alt_paths = [
                os.path.join(CONTENT_PATH, 'content_items.json'),
                os.path.join(CONTENT_PATH, 'sample', 'movies.json'),
                os.path.join(CONTENT_PATH, 'sample', 'content_items.json')
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    content_path = path
                    break
            else:
                logger.warning(f"Could not find content items file in {CONTENT_PATH}, using sample data")
                # Create fallback sample data
                return create_sample_content_items()
        
        with open(content_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading content items: {str(e)}", exc_info=True)
        return create_sample_content_items()

# Function to create sample content items when real data is unavailable
def create_sample_content_items():
    """Create sample content items for testing when real data is not available"""
    logger.info("Creating sample content items for fallback")
    
    # Basic sample movies
    sample_items = [
        {
            "content_id": "sample1",
            "title": "Sample Movie 1",
            "description": "This is a sample movie for testing",
            "genres": ["Action", "Adventure"],
            "year": 2023
        },
        {
            "content_id": "sample2",
            "title": "Sample Movie 2",
            "description": "Another sample movie for testing",
            "genres": ["Comedy", "Romance"],
            "year": 2022
        },
        {
            "content_id": "sample3",
            "title": "Sample Movie 3",
            "description": "A drama sample movie",
            "genres": ["Drama", "Thriller"],
            "year": 2021
        },
        {
            "content_id": "sample4",
            "title": "Sample Documentary",
            "description": "A sample documentary",
            "genres": ["Documentary"],
            "year": 2020
        },
        {
            "content_id": "sample5",
            "title": "Sample Sci-Fi",
            "description": "A science fiction sample",
            "genres": ["Science Fiction", "Adventure"],
            "year": 2019
        }
    ]
    
    # Try to save the sample data for future use
    try:
        os.makedirs(os.path.join(CONTENT_PATH, 'sample'), exist_ok=True)
        sample_path = os.path.join(CONTENT_PATH, 'sample', 'sample_movies.json')
        with open(sample_path, 'w') as f:
            json.dump(sample_items, f)
        logger.info(f"Saved sample content items to {sample_path}")
    except Exception as e:
        logger.error(f"Could not save sample data: {str(e)}")
    
    return sample_items

# Function to get content item by ID
def get_content_item(content_id):
    content_items = get_content_items()
    for item in content_items:
        if str(item.get("content_id")) == str(content_id):
            return item
    return None

@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    limit: int = 10,
    genre: Optional[str] = None,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized recommendations for the logged-in user"""
    try:
        # Load the model if it's not already loaded
        model = load_model()
        model_version = "latest"
        
        # Load content items
        content_items = get_content_items()
        if not content_items:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load content items"
            )
            
        content_dict = {str(item["content_id"]): item for item in content_items}
        
        if model is None:
            # Use fallback recommendation strategy based on popularity
            logger.warning("Model not loaded, using fallback recommendations")
            
            # Get all interactions and count them by content_id
            interactions = db.query(InteractionDB).all()
            
            # Count occurrences of each content_id
            content_counts = {}
            for interaction in interactions:
                content_id = str(interaction.content_id)
                if content_id not in content_counts:
                    content_counts[content_id] = 0
                content_counts[content_id] += 1
            
            # Sort by count (popularity)
            sorted_content = sorted(content_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Filter by genre if specified
            recommendations = []
            for content_id, count in sorted_content:
                if len(recommendations) >= limit:
                    break
                    
                # Get content item
                content_item = content_dict.get(content_id)
                if content_item is None:
                    continue
                    
                # Check genre filter
                if genre and genre not in content_item.get("genres", []):
                    continue
                    
                # Add to recommendations
                recommendations.append(RecommendationItem(
                    content_id=content_id,
                    title=content_item.get("title", "Unknown"),
                    description=content_item.get("description", ""),
                    genres=content_item.get("genres", []),
                    year=content_item.get("year"),
                    score=0.5  # Default score for fallback recommendations
                ))
            
            return RecommendationResponse(
                user_id=user.id,
                recommendations=recommendations,
                model_version="fallback",
                message="Using fallback recommendations based on popularity"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recommendations: {str(e)}")
        return RecommendationResponse(
            user_id=user.id,
            recommendations=[],
            model_version="error",
            message=f"Error generating recommendations: {str(e)}"
        )