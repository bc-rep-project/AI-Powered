from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api import recommendations, auth, monitoring, experiments, rbac
from app.training.task_manager import task_manager
from app.docs.descriptions import TAGS
from prometheus_client import make_asgi_app
import asyncio

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Apply security globally
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    # Start training task manager in the background
    asyncio.create_task(task_manager.start())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown."""
    await task_manager.stop()

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
    Basic health check endpoint.
    Returns status 'healthy' if the service is running properly.
    """
    return {"status": "healthy"}

# Add this at the end of the file
if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False) 