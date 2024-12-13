from fastapi import APIRouter
from app.core.monitoring import get_system_metrics

router = APIRouter()

@router.get("/health")
async def health_check():
    metrics = get_system_metrics()
    return {
        "status": "healthy" if metrics["errors_last_hour"] < 100 else "degraded",
        "metrics": metrics,
        "version": "1.0.0"
    } 