from sqlalchemy.orm import Session
from ..models.user import UserInDB
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_by_email(db, email: str) -> Optional[UserInDB]:
    """Get user by email with support for both sync and async sessions"""
    # Check if the session is async
    if hasattr(db, 'execute') and callable(getattr(db, 'execute')):
        try:
            # Try async approach
            result = await db.execute(select(UserInDB).filter(UserInDB.email == email))
            return result.scalars().first()
        except (TypeError, AttributeError):
            # Fall back to sync approach if await fails
            pass
    
    # Default to synchronous approach
    return db.query(UserInDB).filter(UserInDB.email == email).first()

async def get_user_by_username(db, username: str) -> Optional[UserInDB]:
    """Get user by username with support for both sync and async sessions"""
    # Check if the session is async
    if hasattr(db, 'execute') and callable(getattr(db, 'execute')):
        try:
            # Try async approach
            result = await db.execute(select(UserInDB).filter(UserInDB.username == username))
            return result.scalars().first()
        except (TypeError, AttributeError):
            # Fall back to sync approach if await fails
            pass
    
    # Default to synchronous approach
    return db.query(UserInDB).filter(UserInDB.username == username).first()