from sqlalchemy.orm import Session
from ..models.user import UserInDB
from typing import Optional

async def get_user_by_email(db: Session, email: str) -> Optional[UserInDB]:
    return db.query(UserInDB).filter(UserInDB.email == email).first()

async def get_user_by_username(db: Session, username: str) -> Optional[UserInDB]:
    return db.query(UserInDB).filter(UserInDB.username == username).first()