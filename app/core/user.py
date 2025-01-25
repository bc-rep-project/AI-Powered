from sqlalchemy.orm import Session
from ..models.user import UserInDB
from typing import Optional

async def get_user_by_email(email: str) -> Optional[User]:
    user = await mongodb.users.find_one({"email": email})
    if user:
        return User(**user)
    return None

async def get_user_by_username(db: Session, username: str):
    return db.query(UserInDB).filter(UserInDB.username == username).first()