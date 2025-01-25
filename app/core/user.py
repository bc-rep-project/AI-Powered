from sqlalchemy.orm import Session
from ..models.user import UserInDB

async def get_user_by_email(db: Session, email: str):
    return db.query(UserInDB).filter(UserInDB.email == email).first()

async def get_user_by_username(db: Session, username: str):
    return db.query(UserInDB).filter(UserInDB.username == username).first()