from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, health, recommendations, external
from .core.config import settings
from .database import init_db
from .db.mongodb import mongodb
from .db.redis import redis_client
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.middleware("http")
async def global_error_handler(request: Request, call_next):
    try:
        response = await call_next(request)
        # Handle streaming responses differently
        if hasattr(response, 'body'):
            if response.status_code >= 400:
                return JSONResponse(
                    content={
                        "detail": response.body.decode('utf-8') if response.body else "Unknown error",
                        "status_code": response.status_code
                    },
                    status_code=response.status_code
                )
        return response
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "status_code": 500
            }
        )

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    
    # Create database tables if they don't exist
    try:
        logger.info("Creating database tables if they don't exist...")
        init_db()
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
    
    # Connect to MongoDB
    try:
        await mongodb.connect()
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB: {str(e)}")
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {str(e)}")
    
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Environment: {'development' if 'localhost' in settings.FRONTEND_URL else 'production'}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    try:
        await mongodb.close()
    except:
        pass
    try:
        await redis_client.close()
    except:
        pass

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "message": "AI Content Recommendation API"}

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
app.include_router(recommendations.router, prefix=settings.API_V1_STR, tags=["recommendations"])
app.include_router(external.router, prefix=settings.API_V1_STR, tags=["external"])