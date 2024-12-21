from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api import recommendations, auth, monitoring, experiments, rbac
from app.training.task_manager import task_manager
from app.docs.descriptions import TAGS
from prometheus_client import make_asgi_app
import asyncio
from datetime import datetime
import logging
from app.middleware.rate_limit import setup_rate_limiting, limit_requests
from app.database import test_database_connection, mongodb
import os

app = FastAPI(
    title="AI Content Recommendation Engine",
    description="""
    A powerful recommendation engine that provides personalized content suggestions
    based on user behavior and preferences. Features include:
    
    * Personalized content recommendations
    * User behavior tracking
    * A/B testing capabilities
    * Real-time model updates
    * Performance monitoring
    * Role-based access control
    
    ## Authentication
    
    All API endpoints require authentication using JWT tokens.
    1. Register a new user account
    2. Login to get an access token
    3. Include the token in the Authorization header
    
    ## Roles and Permissions
    
    The system uses role-based access control (RBAC):
    * Admin: Full system access
    * Content Manager: Manage content and view recommendations
    * Experimenter: Manage and run A/B tests
    * Analyst: View and analyze system data
    * Basic User: View content and recommendations
    
    ## Getting Started
    
    1. Create a user account using `/api/v1/auth/register`
    2. Get an access token using `/api/v1/auth/token`
    3. Start getting recommendations using `/api/v1/recommendations`
    
    ## Documentation
    
    * Detailed API documentation: `/docs`
    * Alternative documentation: `/redoc`
    * OpenAPI specification: `/openapi.json`
    """,
    version="1.0.0",
    openapi_tags=list(TAGS.values())
)

# Configure CORS
origins = [
    "http://localhost:3000",  # Frontend development server
    "http://localhost:8000",  # Backend development server
    "https://your-production-domain.com"  # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth.router)
app.include_router(recommendations.router)
app.include_router(monitoring.router)
app.include_router(experiments.router)
app.include_router(rbac.router)

# Setup rate limiting
setup_rate_limiting(app)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="AI Recommendation API",
        version="1.0.0",
        description="API for AI-powered content recommendations",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize connections and resources on startup"""
    logger.info("Starting application...")
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URI")
    if not mongodb_url:
        raise RuntimeError("MONGODB_URI environment variable not set")
        
    if not await mongodb.connect_to_mongodb(mongodb_url):
        raise RuntimeError("MongoDB connection failed")
    
    # Test database connections
    try:
        # Test PostgreSQL
        if not test_database_connection():
            logger.error("Failed to connect to PostgreSQL")
            raise RuntimeError("PostgreSQL connection failed")
            
        # Test MongoDB
        await mongodb.db.command('ping')
        logger.info("Successfully connected to MongoDB")
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    
    # Start training task manager
    asyncio.create_task(task_manager.start())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await task_manager.stop()
    await mongodb.close_mongodb_connection()

@app.get("/", tags=["Root"])
async def root():
    """
    Welcome endpoint with links to documentation.
    """
    return {
        "message": "Welcome to the AI Content Recommendation Engine API",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint that verifies service and database connections.
    """
    try:
        # Check PostgreSQL
        from app.database import test_database_connection
        postgres_ok = test_database_connection()
        
        # Check MongoDB
        await mongodb.db.command('ping')
        mongo_ok = True
        
        return {
            "status": "healthy" if postgres_ok and mongo_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "databases": {
                "postgresql": "connected" if postgres_ok else "failed",
                "mongodb": "connected" if mongo_ok else "failed"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# Example usage on endpoint
@app.get("/api/recommendations")
@limit_requests("5/minute")
async def get_recommendations(request: Request):
    """Get personalized recommendations for the user"""
    return {"recommendations": []}

# Add this at the end of the file
if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False) 