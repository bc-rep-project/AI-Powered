from sqlalchemy.orm import Session
from ..models.user import UserInDB
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import AsyncSession

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserInDB]:
    result = await db.execute(select(UserInDB).filter(UserInDB.email == email))
    return result.scalars().first()

async def get_user_by_username(db: Session, username: str) -> Optional[UserInDB]:
    result = await db.execute(select(UserInDB).filter(UserInDB.username == username))
    return result.scalars().first()