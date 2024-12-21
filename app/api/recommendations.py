from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.auth import get_current_user
from app.models.user import User
from app.models.recommendation import RecommendationResponse, PaginatedResponse
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"]
)

@router.get("/", response_model=PaginatedResponse[RecommendationResponse])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    min_score: Optional[float] = Query(None, ge=0, le=1)
):
    """Get personalized recommendations with pagination and filtering."""
    try:
        # Generate dummy recommendations
        all_recommendations = [
            RecommendationResponse(
                id=str(uuid.uuid4()),
                title=f"Recommendation {i}",
                description=f"Description for recommendation {i}",
                content_id=str(uuid.uuid4()),
                score=0.9 - (i * 0.1),
                category="test",
                created_at=datetime.now(),
                metadata={
                    "tags": ["ai", "technology"],
                    "readTime": f"{5 + i} min"
                }
            )
            for i in range(20)
        ]

        # Apply filters
        filtered_recommendations = all_recommendations
        if category:
            filtered_recommendations = [r for r in filtered_recommendations if r.category == category]
        if min_score is not None:
            filtered_recommendations = [r for r in filtered_recommendations if r.score >= min_score]

        # Apply pagination
        total = len(filtered_recommendations)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_recommendations = filtered_recommendations[start_idx:end_idx]

        return {
            "items": paginated_recommendations,
            "total": total,
            "page": page,
            "totalPages": (total + limit - 1) // limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )

@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific recommendation by ID."""
    try:
        # In a real application, you would fetch this from your database
        recommendation = RecommendationResponse(
            id=recommendation_id,
            title="Sample Recommendation",
            description="Detailed description",
            content_id=str(uuid.uuid4()),
            score=0.95,
            category="test",
            created_at=datetime.now()
        )
        return recommendation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation not found: {str(e)}"
        ) 