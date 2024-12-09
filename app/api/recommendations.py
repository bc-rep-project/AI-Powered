from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List
from app.models.recommendation import UserProfile, ContentItem, Recommendation, UserInteraction
from app.models.user import User
from app.services.recommendation_service import RecommendationService
from app.core.auth import get_current_user
from app.core.monitoring import monitor_endpoint, metrics_logger

router = APIRouter(prefix="/api/v1")
recommendation_service = RecommendationService()

@router.post("/recommendations")
@monitor_endpoint("get_recommendations")
async def get_recommendations(
    request: Request,
    n_recommendations: int = 10,
    current_user: User = Depends(get_current_user)
) -> List[Recommendation]:
    """
    Get personalized recommendations for the authenticated user.
    """
    user_profile = UserProfile(user_id=current_user.id)
    
    try:
        recommendations = await recommendation_service.generate_recommendations(
            user_profile,
            n_recommendations
        )
        return recommendations
    except Exception as e:
        metrics_logger.log_error(
            "recommendation_error",
            str(e),
            {"user_id": current_user.id}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interactions")
@monitor_endpoint("record_interaction")
async def record_interaction(
    request: Request,
    interaction: UserInteraction,
    current_user: User = Depends(get_current_user)
):
    """
    Record a user interaction with content.
    """
    # Verify the interaction is for the authenticated user
    if interaction.user_id != current_user.id:
        metrics_logger.log_error(
            "unauthorized_interaction",
            "User tried to record interaction for another user",
            {"user_id": current_user.id, "target_user_id": interaction.user_id}
        )
        raise HTTPException(
            status_code=403,
            detail="Cannot record interactions for other users"
        )
    
    try:
        # Store interaction and update recommendations
        await recommendation_service.record_interaction(interaction)
        
        # Update user profile
        user_profile = UserProfile(
            user_id=current_user.id,
            interaction_history=[interaction.dict()]
        )
        await recommendation_service.update_user_profile(user_profile)
        
        return {"status": "success", "message": "Interaction recorded"}
    except Exception as e:
        metrics_logger.log_error(
            "interaction_error",
            str(e),
            {"user_id": current_user.id, "interaction": interaction.dict()}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/content")
@monitor_endpoint("add_content")
async def add_content(
    request: Request,
    content_item: ContentItem,
    current_user: User = Depends(get_current_user)
):
    """
    Add new content item to the recommendation system.
    """
    try:
        await recommendation_service.add_content_item(content_item)
        return {"status": "success", "message": "Content item added"}
    except Exception as e:
        metrics_logger.log_error(
            "content_error",
            str(e),
            {"content_id": content_item.content_id}
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content/{content_id}")
@monitor_endpoint("get_content")
async def get_content(
    request: Request,
    content_id: str,
    current_user: User = Depends(get_current_user)
) -> ContentItem:
    """
    Get content item details.
    """
    try:
        return recommendation_service._get_content_item(content_id)
    except Exception as e:
        metrics_logger.log_error(
            "content_fetch_error",
            str(e),
            {"content_id": content_id}
        )
        raise HTTPException(status_code=404, detail="Content not found") 