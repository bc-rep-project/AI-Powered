from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..services.recommendation import RecommendationEngine
from pydantic import BaseModel

router = APIRouter()

class Recommendation(BaseModel):
    content_id: int
    title: str
    type: str
    score: float

@router.get("/recommendations/", response_model=List[Recommendation])
async def get_recommendations(
    user_id: int,
    content_type: Optional[str] = None,
    method: str = "hybrid",
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get personalized recommendations for a user.
    Method can be one of: 'collaborative', 'content-based', or 'hybrid'
    """
    try:
        engine = RecommendationEngine(db)
        
        if method == "collaborative":
            recommendations = await engine.get_collaborative_recommendations(
                user_id=user_id,
                limit=limit
            )
        elif method == "content-based":
            recommendations = await engine.get_content_based_recommendations(
                user_id=user_id,
                content_type=content_type,
                limit=limit
            )
        elif method == "hybrid":
            # Get both types of recommendations
            collaborative_recs = await engine.get_collaborative_recommendations(
                user_id=user_id,
                limit=limit
            )
            content_based_recs = await engine.get_content_based_recommendations(
                user_id=user_id,
                content_type=content_type,
                limit=limit
            )
            
            # Combine and sort by score
            seen_content_ids = set()
            recommendations = []
            
            # Merge recommendations with weights
            for rec in collaborative_recs:
                if rec["content_id"] not in seen_content_ids:
                    rec["score"] *= 0.6  # Weight for collaborative filtering
                    recommendations.append(rec)
                    seen_content_ids.add(rec["content_id"])
            
            for rec in content_based_recs:
                if rec["content_id"] not in seen_content_ids:
                    rec["score"] *= 0.4  # Weight for content-based filtering
                    recommendations.append(rec)
                    seen_content_ids.add(rec["content_id"])
            
            # Sort by score and limit results
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            recommendations = recommendations[:limit]
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid method. Use 'collaborative', 'content-based', or 'hybrid'"
            )
        
        return recommendations
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 