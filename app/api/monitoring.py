from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.monitoring import (
    REQUESTS_TOTAL,
    REQUEST_LATENCY,
    SYSTEM_INFO,
    metrics_logger
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

@router.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy"} 