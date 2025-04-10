from sqlalchemy.orm import Session
from ..models.user import UserInDB
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

async def get_user_by_email(db, email: str) -> Optional[UserInDB]:
    """Get user by email with support for both sync and async sessions"""
    if not email:
        logger.warning("Email parameter is empty in get_user_by_email")
        return None
        
    # Normalize email to lowercase
    email = email.lower()
    
    try:
        # Check if the session is async
        if hasattr(db, 'execute') and callable(getattr(db, 'execute')):
            try:
                # Try async approach
                result = await db.execute(select(UserInDB).filter(UserInDB.email == email))
                return result.scalars().first()
            except (TypeError, AttributeError) as e:
                # Fall back to sync approach if await fails
                logger.warning(f"Async session failed, falling back to sync: {str(e)}")
        
        # Default to synchronous approach
        return db.query(UserInDB).filter(UserInDB.email == email).first()
    except Exception as e:
        logger.error(f"Error in get_user_by_email: {str(e)}", exc_info=True)
        return None

async def get_user_by_username(db, username: str) -> Optional[UserInDB]:
    """Get user by username with support for both sync and async sessions"""
    if not username:
        logger.warning("Username parameter is empty in get_user_by_username")
        return None
        
    try:
        # Check if the session is async
        if hasattr(db, 'execute') and callable(getattr(db, 'execute')):
            try:
                # Try async approach
                result = await db.execute(select(UserInDB).filter(UserInDB.username == username))
                return result.scalars().first()
            except (TypeError, AttributeError) as e:
                # Fall back to sync approach if await fails
                logger.warning(f"Async session failed, falling back to sync: {str(e)}")
        
        # Default to synchronous approach
        return db.query(UserInDB).filter(UserInDB.username == username).first()
    except Exception as e:
        logger.error(f"Error in get_user_by_username: {str(e)}", exc_info=True)
        return None

# Add a function to handle both email and username lookups
async def get_user_by_identifier(db, identifier: str) -> Optional[UserInDB]:
    """Lookup user by either email or username"""
    if not identifier:
        logger.warning("Identifier parameter is empty in get_user_by_identifier")
        return None
        
    # First try email lookup
    user = await get_user_by_email(db, identifier)
    if user:
        return user
        
    # Then try username lookup
    return await get_user_by_username(db, identifier)