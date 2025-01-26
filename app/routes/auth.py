from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from typing import Optional
import uuid
from sqlalchemy.orm import Session
from ..core.config import settings
from ..database import get_db
from ..models.user import UserInDB, UserCreate, User, Token, TokenData
from ..core.auth import get_current_user, get_user_by_email
from ..core.user import get_user_by_email, get_user_by_username
import logging
from ..db.redis import redis_client, get_redis
from redis import asyncio as aioredis
from pydantic import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/token")

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# Database operations
def get_user_by_email(db: Session, email: str):
    return db.query(UserInDB).filter(UserInDB.email.ilike(email)).first()

def get_user_by_username(db: Session, username: str):
    return db.query(UserInDB).filter(UserInDB.username.ilike(username)).first()

def create_user(db: Session, user_data: dict):
    try:
        db_user = UserInDB(
            id=str(uuid.uuid4()),
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=user_data["hashed_password"],
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise e

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Routes
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Normalize email and username
        user.email = user.email.strip().lower()
        user.username = user.username.strip()
        
        # Check if email or username exists
        existing_email = get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_username = get_user_by_username(db, user.username)
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")

        # Validate password strength
        if len(user.password) < 8:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 8 characters"
            )

        hashed_password = get_password_hash(user.password)
        user_data = {
            "email": user.email,
            "username": user.username,
            "hashed_password": hashed_password,
            "is_active": True
        }
        
        new_user = create_user(db, user_data)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        
        return {
            "message": "User created successfully",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(new_user.id)
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=e.errors()
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again later."
        )

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Use form_data.username as email since we're using email for authentication
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(
    redis: aioredis.Redis = Depends(get_redis),
    token: str = Depends(oauth2_scheme)
):
    try:
        if not token:
            raise HTTPException(status_code=400, detail="No token provided")
        
        # Add token to blacklist
        await redis.setex(
            f"blacklist:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "true"
        )
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Logout failed. Please try again."
        )