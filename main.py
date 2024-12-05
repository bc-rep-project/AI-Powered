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
        "https://ai-powered-content-recommendation-frontend-kslis1lqp.vercel.app",
        "*"  # During development - remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secure-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Initialize recommendation model
recommendation_model = RecommendationModel()

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    try:
        # Initialize database connection
        await Database.connect_db()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    try:
        await Database.close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")

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

# ... (keep existing route handlers) ...