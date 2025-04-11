from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, recommendations, external, data, dataset, admin
from .routes import health as health_router  # Rename the import to avoid collision
from .routes import training  # Import the training router
from .core.config import settings
import logging
import importlib
import os
import gc
from datetime import datetime, timedelta
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio

logger = logging.getLogger(__name__)

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add rate limiter to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    """Initialize application on startup"""
    try:
        logger.info("Starting up application...")
        
        # Initialize database tables
        try:
            from .db.init_db import init_db
            db_init_success = await init_db()
            if db_init_success:
                logger.info("Database tables initialized successfully")
                
                # Run database migrations after initializing tables
                try:
                    from .db.database import engine
                    from .db.migrations import run_all_migrations
                    success_count, failure_count = await run_all_migrations(engine)
                    if failure_count == 0:
                        logger.info(f"All {success_count} database migrations completed successfully")
                    else:
                        logger.warning(f"Database migrations completed with {failure_count} failures out of {success_count + failure_count}")
                except Exception as migration_err:
                    logger.error(f"Error running database migrations: {str(migration_err)}")
            else:
                logger.warning("Database tables initialization incomplete - some features may not work")
        except Exception as db_err:
            logger.error(f"Error initializing database: {str(db_err)}")
        
        # Check for free tier optimizations
        from .utils.render_optimizer import is_render_free_tier, start_render_optimizer
        if is_render_free_tier():
            logger.info("Running on Render free tier, starting optimizer")
            start_render_optimizer()
        else:
            logger.info("Render optimizer not needed for this environment")
            
        # Connect to MongoDB
        try:
            from .db.mongodb import mongodb
            await mongodb.connect()
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"MongoDB connection error: {str(e)}")
            
        # Check Redis connection
        try:
            from .db.redis import redis_client
            if redis_client:
                # Use the correct async syntax for Redis or handle synchronous client
                if hasattr(redis_client, 'ping') and callable(redis_client.ping):
                    # Try to determine if it's an async Redis client
                    if asyncio.iscoroutinefunction(redis_client.ping):
                        await redis_client.ping()
                    else:
                        # Handle synchronous Redis client
                        redis_client.ping()
                logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
        
        # Start job queue cleanup scheduler
        try:
            # Import the job queue module
            importlib.import_module('.services.job_queue', package='app')
            # Start the cleanup scheduler as a background task
            from .services.job_queue import start_cleanup_scheduler
            background_task = asyncio.create_task(start_cleanup_scheduler())
            # Store task reference to prevent garbage collection
            app.state.job_queue_task = background_task
            logger.info("Started job queue cleanup scheduler")
        except Exception as job_err:
            logger.error(f"Error starting job queue cleanup scheduler: {str(job_err)}")
            
        # Configuration info
        logger.info(f"API Version: {settings.API_V1_STR}")
        logger.info(f"Environment: {'production' if os.getenv('ENV') == 'production' else 'development'}")
        
        # Start model retraining scheduler
        if os.getenv("ENABLE_AUTO_RETRAINING", "true").lower() == "true":
            try:
                from .services.scheduler import init_scheduler
                
                # Get config values or use defaults
                interval_hours = int(os.getenv("MODEL_RETRAINING_INTERVAL_HOURS", "24"))
                interaction_threshold = int(os.getenv("MODEL_RETRAINING_INTERACTION_THRESHOLD", "200"))
                
                # Start scheduler
                scheduler = init_scheduler(
                    retraining_interval_hours=interval_hours,
                    interaction_threshold=interaction_threshold
                )
                scheduler.start()
                logger.info(f"Model retraining scheduler started with interval {interval_hours} hours and threshold {interaction_threshold} interactions")
            except Exception as e:
                logger.error(f"Error starting model retraining scheduler: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    
    # Stop the scheduler if it's running
    try:
        from .services.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            scheduler.stop()
            logger.info("Model retraining scheduler stopped")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
    
    # Close database connections
    try:
        from .db.mongodb import mongodb
        await mongodb.close()
        logger.info("MongoDB connection closed")
    except (ImportError, AttributeError):
        pass
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {str(e)}")
    
    try:
        from .db.redis import redis_client
        await redis_client.close()
        logger.info("Redis connection closed")
    except (ImportError, AttributeError):
        pass
    except Exception as e:
        logger.error(f"Error closing Redis connection: {str(e)}")

# Root endpoint for health check
@app.get("/")
async def root():
    """Root endpoint for health checks."""
    return {
        "status": "healthy",
        "message": "AI Content Recommendation API",
        "version": "1.0.0",
        "docs_url": f"{settings.API_V1_STR}/docs"
    }

# Simple ping endpoint to keep the app alive
@app.get("/ping")
@limiter.limit("10/minute")
async def ping(request: Request):
    """Simple endpoint for keeping the app alive. Can be pinged by an external service."""
    gc.collect()  # Run garbage collection to free memory
    memory_info = {}
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = {
            "memory_percent": process.memory_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024
        }
    except ImportError:
        memory_info = {"message": "psutil not available"}
    
    return {
        "status": "alive", 
        "timestamp": datetime.now().isoformat(),
        "memory": memory_info
    }

# Direct health check endpoint (without API prefix)
@app.get("/health")
async def health():
    """Direct health check endpoint (no API prefix)."""
    try:
        # Try to call the API health check
        from .routes.health import health_check
        return await health_check()
    except Exception as e:
        # Log the error but return a degraded status
        logger.error(f"Health check error: {str(e)}")
        
        # Return a simple health status
        return {
            "status": "degraded",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENV", "development"),
            "resources": {
                "message": "Health check encountered an error"
            }
        }

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(health_router.router, prefix=settings.API_V1_STR, tags=["health"])  # Use the renamed import
app.include_router(recommendations.router, prefix=settings.API_V1_STR, tags=["recommendations"])
app.include_router(external.router, prefix=settings.API_V1_STR, tags=["external"])
app.include_router(data.router, prefix=settings.API_V1_STR, tags=["data"])
app.include_router(dataset.router, prefix=settings.API_V1_STR, tags=["dataset"])
app.include_router(admin.router, prefix=settings.API_V1_STR, tags=["admin"])

# Add the training router last to avoid any routing conflicts
try:
    app.include_router(training.router, prefix=settings.API_V1_STR, tags=["training"])
    logger.info("Training router added successfully")
except Exception as e:
    logger.error(f"Error adding training router: {str(e)}")