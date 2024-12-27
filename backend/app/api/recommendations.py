from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..core.auth import get_current_user
from ..ml.models.recommender import RecommenderModel
from ..data.processing.features import process_user_data

router = APIRouter()

class ContentRecommendation(BaseModel):
    id: str
    title: str
    description: str
    category: str
    score: float
    tags: List[str]
    created_at: datetime
    relevance_explanation: str

class RecommendationRequest(BaseModel):
    user_id: str
    context: Optional[dict] = None
    limit: Optional[int] = 10
    filters: Optional[dict] = None

@router.get("/recommendations", response_model=List[ContentRecommendation])
async def get_recommendations(
    limit: int = 10,
    category: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get personalized recommendations for the current user."""
    try:
        # Get user interaction history and preferences
        user_data = process_user_data(current_user.id)
        
        # Get recommendations from the model
        recommender = RecommenderModel()
        recommendations = recommender.get_recommendations(
            user_id=current_user.id,
            user_data=user_data,
            limit=limit,
            category=category
        )
        
        return recommendations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.post("/recommendations/feedback")
async def submit_feedback(
    content_id: str,
    feedback_type: str,
    rating: Optional[float] = None,
    current_user = Depends(get_current_user)
):
    """Submit user feedback for a recommendation."""
    try:
        # Store user feedback
        feedback = {
            "user_id": current_user.id,
            "content_id": content_id,
            "feedback_type": feedback_type,
            "rating": rating,
            "timestamp": datetime.utcnow()
        }
        
        # Update user interaction history
        # This will be used in future recommendations
        await update_user_interactions(feedback)
        
        return {"message": "Feedback submitted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )

@router.get("/recommendations/explore")
async def explore_recommendations(
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    current_user = Depends(get_current_user)
):
    """Get diverse recommendations for exploration."""
    try:
        recommender = RecommenderModel()
        recommendations = recommender.get_diverse_recommendations(
            user_id=current_user.id,
            category=category,
            tags=tags,
            limit=limit
        )
        
        return recommendations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get exploration recommendations: {str(e)}"
        )

async def update_user_interactions(feedback: dict):
    """Update user interaction history in the database."""
    # TODO: Implement database update
    pass 