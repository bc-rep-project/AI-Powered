from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, health, recommendations
from .core.config import settings
from .db.mongodb import mongodb
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.middleware("http")
async def global_error_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "https://ai-powered-content-recommendation-frontend.vercel.app",
        "https://ai-recommendation-api.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up application...")
    await mongodb.connect()
    logger.info(f"API Version: {settings.API_V1_STR}")
    logger.info(f"Environment: {'development' if 'localhost' in settings.FRONTEND_URL else 'production'}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application...")
    await mongodb.close()

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "message": "AI Content Recommendation API"}

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])
app.include_router(recommendations.router, prefix=settings.API_V1_STR, tags=["recommendations"]) 