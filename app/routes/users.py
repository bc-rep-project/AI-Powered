from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from app.models.user import User
from app.db.database import get_db
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)

class UserPreferences(BaseModel):
    categories: list[str]
    difficulty: str
    language: str

@router.put("/preferences")
async def update_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Update user preferences in PostgreSQL
        db_user = db.query(User).filter(User.id == current_user.id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
            
        db_user.preferences = preferences.dict()
        db.commit()
        
        # Also update in MongoDB for recommendations
        await mongodb.users.update_one(
            {"email": current_user.email},
            {"$set": {"preferences": preferences.dict()}},
            upsert=True
        )
        
        return {"status": "preferences updated"}
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update preferences") 