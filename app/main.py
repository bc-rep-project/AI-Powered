from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, health
from .core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint for health check
@app.get("/")
async def root():
    return {"status": "healthy", "message": "AI Content Recommendation API"}

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["auth"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"]) 