from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.models.user import User
from app.core.auth import get_current_user
from app.core.monitoring import (
    REQUESTS_TOTAL,
    RESPONSE_TIME,
    MODEL_TRAINING_TIME,
    ACTIVE_USERS,
    RECOMMENDATION_QUALITY,
    CACHE_HITS,
    CACHE_MISSES,
    monitor_endpoint
)
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import json

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])

@router.get("/metrics")
@monitor_endpoint("get_metrics")
async def get_metrics(current_user: User = Depends(get_current_user)):
    """Get Prometheus metrics."""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@router.get("/stats")
@monitor_endpoint("get_stats")
async def get_stats(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get system statistics."""
    try:
        # Collect metrics
        stats = {
            "requests": {
                "total": REQUESTS_TOTAL._value.sum(),
                "by_endpoint": {
                    label_dict["endpoint"]: value
                    for label_dict, value in REQUESTS_TOTAL._metrics.items()
                }
            },
            "response_times": {
                "average": RESPONSE_TIME._sum.sum() / RESPONSE_TIME._count.sum()
                if RESPONSE_TIME._count.sum() > 0 else 0,
                "by_endpoint": {
                    label_dict["endpoint"]: value / count
                    for (label_dict, value), count in zip(
                        RESPONSE_TIME._sum._metrics.items(),
                        RESPONSE_TIME._count._metrics.values()
                    )
                    if count > 0
                }
            },
            "model_training": {
                "average_duration": MODEL_TRAINING_TIME._sum.sum() / MODEL_TRAINING_TIME._count.sum()
                if MODEL_TRAINING_TIME._count.sum() > 0 else 0,
                "total_trainings": MODEL_TRAINING_TIME._count.sum()
            },
            "users": {
                "active": ACTIVE_USERS._value
            },
            "recommendation_quality": {
                label_dict["metric"]: value
                for label_dict, value in RECOMMENDATION_QUALITY._metrics.items()
            },
            "cache": {
                "hits": {
                    label_dict["cache_type"]: value
                    for label_dict, value in CACHE_HITS._metrics.items()
                },
                "misses": {
                    label_dict["cache_type"]: value
                    for label_dict, value in CACHE_MISSES._metrics.items()
                }
            }
        }
        
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching metrics: {str(e)}"
        )

@router.get("/health/detailed")
@monitor_endpoint("get_health_detailed")
async def get_health_detailed(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get detailed system health information."""
    try:
        # Calculate error rates
        total_requests = REQUESTS_TOTAL._value.sum()
        error_requests = sum(
            value
            for label_dict, value in REQUESTS_TOTAL._metrics.items()
            if label_dict["status"] == "500"
        )
        error_rate = error_requests / total_requests if total_requests > 0 else 0
        
        # Calculate cache hit rate
        total_cache_hits = sum(CACHE_HITS._metrics.values())
        total_cache_misses = sum(CACHE_MISSES._metrics.values())
        total_cache_ops = total_cache_hits + total_cache_misses
        cache_hit_rate = total_cache_hits / total_cache_ops if total_cache_ops > 0 else 0
        
        health_status = {
            "status": "healthy" if error_rate < 0.05 else "degraded",
            "error_rate": error_rate,
            "cache_hit_rate": cache_hit_rate,
            "average_response_time": RESPONSE_TIME._sum.sum() / RESPONSE_TIME._count.sum()
            if RESPONSE_TIME._count.sum() > 0 else 0,
            "active_users": ACTIVE_USERS._value,
            "recommendation_quality": {
                label_dict["metric"]: value
                for label_dict, value in RECOMMENDATION_QUALITY._metrics.items()
            }
        }
        
        return health_status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching health status: {str(e)}"
        ) 