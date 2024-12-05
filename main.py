import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
import jwt
from datetime import datetime, timedelta
import logging
from src.database import Database
from src.models.recommendation_model import RecommendationModel
from src.models.data_models import Content, Interaction, UserProfile, RecommendationHistory
from fastapi.routing import APIRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Content Recommendation API",
    description="Provides personalized content recommendations based on user behavior and preferences."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-powered-content-recommendation-frontend.vercel.app",
        "https://ai-powered-content-recommendation-frontend-kslis1lqp.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Authentication settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secure-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize recommendation model
recommendation_model = RecommendationModel()

# API Routes
api_router = APIRouter(prefix="/api/v1")

@api_router.get("/recommendations")
async def get_recommendations(current_user: str = Depends(oauth2_scheme)):
    """Get personalized recommendations."""
    try:
        # Extract user email from token
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        # Get recommendations using the model
        recommendations = recommendation_model.get_recommendations(user_email, n=10)
        
        # Format response
        return {
            "recommendations": recommendations,
            "user": user_email,
            "timestamp": datetime.utcnow().isoformat()
        }
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating recommendations"
        )

# Include API router
app.include_router(api_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    try:
        # Check database connection
        if not await Database.ping_db():
            raise HTTPException(
                status_code=503,
                detail="Database connection failed"
            )
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "service": "online"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to AI Content Recommendation API",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# Token endpoint
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login to get access token."""
    logger.info(f"Login attempt for user: {form_data.username}")
    
    # Add your user verification logic here
    if not form_data.username or not form_data.password:
        logger.error("Missing username or password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing username or password",
        )
    
    try:
        # Here you should verify against your database
        # For now, using a simple check (replace with actual DB verification)
        if form_data.username == "test@example.com" and form_data.password == "password":
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": form_data.username},
                expires_delta=access_token_expires
            )
            response_data = {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
            logger.info(f"Login successful for user: {form_data.username}")
            return response_data
        else:
            logger.warning(f"Invalid credentials for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        logger.error(f"Login error for user {form_data.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ... (keep existing route handlers) ...