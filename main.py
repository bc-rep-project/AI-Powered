import os
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse
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

# Create API routers with proper prefixes and tags
api_router = APIRouter(prefix="/api/v1", tags=["api"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# CORS configuration
origins = [
    "https://ai-powered-content-recommendation-frontend.vercel.app",
    "https://ai-powered-content-recommendation-frontend-kslis1lqp.vercel.app",
    "http://localhost:3000",  # For local development
    "https://diplomatic-heart-production.up.railway.app",  # Railway backend
    "https://ai-powered-production.up.railway.app"  # Railway production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Authentication settings
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secure-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize recommendation model with dummy data
recommendation_model = RecommendationModel()

# Add dummy data for testing
dummy_interactions = [
    {"user_id": "test@example.com", "content_id": "content1", "interaction_type": "view", "timestamp": "2024-01-01"},
    {"user_id": "test@example.com", "content_id": "content2", "interaction_type": "like", "timestamp": "2024-01-02"},
    {"user_id": "test@example.com", "content_id": "content3", "interaction_type": "view", "timestamp": "2024-01-03"},
]

# Train model with dummy data
recommendation_model.train(dummy_interactions, epochs=5, batch_size=32)

# Pydantic models for request/response
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserResponse(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegister):
    """Register a new user."""
    logger.info(f"Registration attempt for user: {user.email}")
    try:
        # Check if user already exists
        existing_user = await Database.find_user(user.email)
        if existing_user:
            logger.warning(f"User already exists: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists"
            )
        
        # Hash password and create user
        hashed_password = Database.hash_password(user.password)
        new_user = {
            "email": user.email,
            "password": hashed_password,
            "name": user.name,
            "created_at": datetime.utcnow()
        }
        
        # Save user to database
        await Database.create_user(new_user)
        logger.info(f"User registered successfully: {user.email}")
        
        return UserResponse(email=user.email, name=user.name)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@api_router.get("/recommendations", response_model=Dict)
async def get_recommendations(current_user: str = Depends(oauth2_scheme)):
    """Get personalized recommendations."""
    logger.info("Received recommendations request")
    try:
        # Extract user email from token
        payload = jwt.decode(current_user, SECRET_KEY, algorithms=[ALGORITHM])
        user_email = payload.get("sub")
        if not user_email:
            logger.error("No user email in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        logger.info(f"Generating recommendations for user: {user_email}")
        # Get recommendations using the model
        recommendations = recommendation_model.get_recommendations(user_email, n=10)
        
        # If no recommendations, return dummy data
        if not recommendations:
            recommendations = [
                {
                    "content_id": f"content{i}",
                    "score": round(0.9 - (i * 0.1), 2),
                    "rank": i + 1,
                    "title": f"Sample Content {i}",
                    "description": f"This is a sample content item {i}",
                    "type": "article" if i % 2 == 0 else "video",
                    "metadata": {
                        "tags": [f"tag{j}" for j in range(3)],
                        "category": f"category{i % 5}"
                    }
                }
                for i in range(5)
            ]
        
        # Format response
        response = {
            "status": "success",
            "recommendations": recommendations,
            "user": user_email,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "count": len(recommendations),
                "model_version": recommendation_model.version,
                "algorithm": recommendation_model.algorithm_type
            }
        }
        logger.info(f"Generated {len(recommendations)} recommendations")
        return response
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
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

# Token endpoint
@app.post("/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login to get access token."""
    logger.info(f"Login attempt for user: {form_data.username}")
    
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
            response_data = TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
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
# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway deployment"""
    try:
        # Check database connection
        await Database.ping_db()
        
        # Check recommendation model status
        model_status = recommendation_model.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "model_status": model_status,
            "environment": os.getenv("ENVIRONMENT", "production")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
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
# Include routers at the end of the file
app.include_router(auth_router)
app.include_router(api_router)

