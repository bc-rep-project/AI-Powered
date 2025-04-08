import sys
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Try to import jwt module, fall back to PyJWT if needed, and install if not available
try:
    import jwt
except ImportError:
    try:
        import PyJWT as jwt
        logging.info("Using PyJWT instead of jwt")
    except ImportError:
        logging.error("Could not import jwt or PyJWT. Installing PyJWT...")
        try:
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "PyJWT>=2.4.0"], check=True)
            import PyJWT as jwt
            logging.info("Successfully installed and imported PyJWT")
        except Exception as e:
            logging.error(f"Failed to install PyJWT: {e}")
            raise RuntimeError("JWT library could not be installed. Please install it manually with 'pip install PyJWT'")

from typing import Optional
import uuid
from sqlalchemy.orm import Session

# Import AsyncSession with proper fallback
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    # For older SQLAlchemy versions or when async is not available
    from sqlalchemy.orm import Session as AsyncSession

from ..core.config import settings
from ..database import get_db
from ..models.user import UserInDB, UserCreate, User, Token, TokenData
from ..core.auth import get_current_user, verify_password, get_password_hash, create_access_token

# Import Redis with error handling
try:
    from ..db.redis import redis_client, get_redis
    from redis import asyncio as aioredis
    redis_available = True
except ImportError:
    logging.warning("Redis not available. Logout functionality will be limited.")
    redis_available = False
    # Define dummy functions
    async def get_redis():
        return None

import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/token")

# Database operations
async def get_user_by_email(db: Session, email: str):
    return db.query(UserInDB).filter(UserInDB.email.ilike(email)).first()

async def get_user_by_username(db: Session, username: str):
    return db.query(UserInDB).filter(UserInDB.username.ilike(username)).first()

async def create_user(db: Session, user_data: dict):
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

async def authenticate_user(db: Session, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Routes
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Normalize email and username
        user.email = user.email.strip().lower()
        user.username = user.username.strip()
        
        # Check if email or username exists
        existing_email = await get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_username = await get_user_by_username(db, user.username)
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
        
        new_user = await create_user(db, user_data)
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
    token: str = Depends(oauth2_scheme)
):
    try:
        if not token:
            raise HTTPException(status_code=400, detail="No token provided")
        
        if not redis_available:
            logger.warning("Redis not available for token blacklisting")
            return {"message": "Logged out successfully (token blacklisting not available)"}
        
        # Get Redis client
        redis = await get_redis()
        if not redis:
            return {"message": "Logged out successfully (token blacklisting not available)"}
            
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