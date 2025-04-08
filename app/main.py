from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, health, recommendations, external, data, dataset, admin
from .core.config import settings
from .db.mongodb import mongodb
from .db.redis import redis_client
from .services.scheduler import init_scheduler, get_scheduler
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
    await mongodb.connect()
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Environment: {'development' if 'localhost' in settings.FRONTEND_URL else 'production'}")
    await redis_client.ping()  # Test Redis connection
    logger.info("Connected to Redis")
    
    # Initialize and start the model retraining scheduler
    try:
        # Get retraining configuration from settings
        retraining_interval = getattr(settings, "MODEL_RETRAINING_INTERVAL_HOURS", 12)
        interaction_threshold = getattr(settings, "MODEL_RETRAINING_INTERACTION_THRESHOLD", 50)
        dataset = getattr(settings, "DATASET_NAME", "movielens-small")
        epochs = getattr(settings, "NUM_EPOCHS", 10)
        batch_size = getattr(settings, "BATCH_SIZE", 64)
        
        # Initialize and start the scheduler
        scheduler = init_scheduler(
            retraining_interval_hours=retraining_interval,
            interaction_threshold=interaction_threshold,
            dataset=dataset,
            epochs=epochs,
            batch_size=batch_size
        )
        scheduler.start()
        logger.info(f"Model retraining scheduler started with interval {retraining_interval} hours and threshold {interaction_threshold} interactions")
    except Exception as e:
        logger.error(f"Error starting model retraining scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    
    # Stop the scheduler if it's running
    scheduler = get_scheduler()
    if scheduler:
        scheduler.stop()
        logger.info("Model retraining scheduler stopped")
    
    await mongodb.close()
    await redis_client.close()

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "message": "AI Content Recommendation API"}

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(recommendations.router, prefix=settings.API_V1_STR, tags=["recommendations"])
app.include_router(external.router, prefix=settings.API_V1_STR, tags=["external"])
app.include_router(data.router, prefix=settings.API_V1_STR, tags=["data"])
app.include_router(dataset.router, prefix=settings.API_V1_STR, tags=["dataset"])
app.include_router(admin.router, prefix=settings.API_V1_STR, tags=["admin"])