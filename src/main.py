from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import auth, recommendations
from src.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Content Recommendation API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper prefixes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["recommendations"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "AI Content Recommendation API is running"} 