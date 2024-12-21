from fastapi import APIRouter, Depends, HTTPException, status
from app.core.auth import get_current_user
from app.models.user import User
from app.models.recommendation import RecommendationResponse
from typing import List
from datetime import datetime
import uuid

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["recommendations"]
)

@router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(current_user: User = Depends(get_current_user)):
    """Get personalized recommendations for the current user."""
    try:
        # Dummy recommendations for testing
        recommendations = [
            RecommendationResponse(
                id=str(uuid.uuid4()),
                title=f"Recommendation {i}",
                description=f"Description for recommendation {i}",
                content_id=str(uuid.uuid4()),
                score=0.9 - (i * 0.1),
                category="test",
                created_at=datetime.now()
            )
            for i in range(5)
        ]
        return recommendations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        ) 