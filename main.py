import os
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import jwt
import logging
from typing import List, Optional, Dict

from src.database import Database
from src.models.recommendation_model import RecommendationModel
from src.models.data_models import Content, Interaction, UserProfile, RecommendationHistory

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
origins = [
    "http://localhost:3000",
    "https://ai-powered-content-recommendation-frontend.vercel.app",
    "https://ai-powered-content-recommendation-frontend-kslis1lqp.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secure-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize recommendation model
recommendation_model = RecommendationModel()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Authentication endpoints
@app.post("/api/v1/auth/register")
async def register(user_data: dict):
    """Register a new user."""
    try:
        user = await Database.create_user(user_data)
        return {"message": "User registered successfully", "user": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login to get access token."""
    try:
        user = await Database.find_user(form_data.username)
        if not user or not Database.verify_password(form_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        access_token = create_access_token(data={"sub": user["email"]})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Content endpoints
@app.get("/api/v1/recommendations")
async def get_recommendations(current_user: str = Depends(oauth2_scheme)):
    """Get personalized recommendations."""
    try:
        recommendations = recommendation_model.get_recommendations(current_user)
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/content/explore")
async def explore_content(current_user: str = Depends(oauth2_scheme)):
    """Explore available content."""
    try:
        content = recommendation_model.get_recommendations(current_user, n=20)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/content/search")
async def search_content(q: str, current_user: str = Depends(oauth2_scheme)):
    """Search content."""
    try:
        content = recommendation_model.get_recommendations(current_user, n=10)
        # Filter by search query (in a real implementation, this would use proper search)
        filtered = [c for c in content if q.lower() in c["title"].lower() or q.lower() in c["description"].lower()]
        return {"results": filtered}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# User endpoints
@app.get("/api/v1/users/favorites")
async def get_favorites(current_user: str = Depends(oauth2_scheme)):
    """Get user's favorite content."""
    try:
        interactions = await Database.get_user_interactions(current_user)
        favorites = [i for i in interactions if i["interaction_type"] == "favorite"]
        return {"favorites": favorites}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/users/settings")
async def get_settings(current_user: str = Depends(oauth2_scheme)):
    """Get user settings."""
    try:
        user = await Database.find_user(current_user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "settings": {
                "email": user["email"],
                "name": user.get("name"),
                "preferences": user.get("preferences", {})
            }
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_access_token(data: dict):
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

