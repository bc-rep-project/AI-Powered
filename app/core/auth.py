from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import TokenData, User, UserInDB
from app.db.database import mongodb
from .config import settings
from ..db.redis import redis_client, get_redis
from sqlalchemy.orm import Session

# Import AsyncSession with proper fallback
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    # For older SQLAlchemy versions or when async is not available
    from sqlalchemy.orm import Session as AsyncSession

# Ensure consistent imports for user functions
try:
    from .user import get_user_by_email, get_user_by_username
except ImportError:
    # Define fallback functions if import fails
    async def get_user_by_email(db, email):
        return db.query(UserInDB).filter(UserInDB.email.ilike(email)).first()
    
    async def get_user_by_username(db, username):
        return db.query(UserInDB).filter(UserInDB.username.ilike(username)).first()

from ..database import get_db

# Security configuration - Updated to use settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        
        # Only check Redis blacklist if Redis client is available
        if redis_client:
            try:
                redis = await get_redis()
                if redis and await redis.exists(f"blacklist:{token}"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked"
                    )
            except Exception as e:
                # If Redis check fails, log but continue
                print(f"Redis check failed: {str(e)}")
        
        user = await get_user_by_email(db, email)
        if not user:
            raise credentials_exception
        return user
    except JWTError as e:
        raise credentials_exception

async def authenticate_user(db, email: str, password: str):
    """Authenticate user with email and password"""
    user = await get_user_by_email(db, email)
    if not user:
        return None  # Return None instead of False for async consistency
    if not verify_password(password, user.hashed_password):
        return None
    return user