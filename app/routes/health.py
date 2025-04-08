from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import os
import logging
from ..core.auth import get_current_user
from ..services.scheduler import get_scheduler
from ..services.interaction_counter import get_interaction_count

# Try to import psutil, but provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. System resource monitoring will be limited.")

router = APIRouter(prefix="/health", tags=["health"])

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    environment: str
    resources: Optional[Dict] = None

@router.get("", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    environment = "production" if os.getenv("ENV") == "production" else "development"
    
    # Gather basic system resources if psutil is available
    resources = None
    if PSUTIL_AVAILABLE:
        resources = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        }
    else:
        resources = {
            "message": "System resource monitoring not available (psutil not installed)"
        }
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        environment=environment,
        resources=resources
    )

class RetrainingStatusResponse(BaseModel):
    is_running: bool
    last_retraining_time: Optional[str] = None
    next_retraining_check: Optional[str] = None
    interaction_count: Optional[int] = None
    interaction_threshold: Optional[int] = None
    retraining_interval_hours: Optional[int] = None

@router.get("/retraining", response_model=RetrainingStatusResponse)
async def retraining_status(user = Depends(get_current_user)):
    """Check the status of the model retraining scheduler"""
    scheduler = get_scheduler()
    
    if not scheduler:
        return RetrainingStatusResponse(
            is_running=False,
            interaction_count=await get_interaction_count()
        )
    
    # Get last retraining time
    last_time = None
    if scheduler.last_retraining_time:
        last_time = scheduler.last_retraining_time.isoformat()
    
    # Calculate next retraining check time
    next_check = None
    if scheduler.last_retraining_time:
        from datetime import timedelta
        next_time = scheduler.last_retraining_time + timedelta(hours=scheduler.retraining_interval_hours)
        next_check = next_time.isoformat()
    
    # Get current interaction count
    interaction_count = await get_interaction_count()
    
    return RetrainingStatusResponse(
        is_running=scheduler.running,
        last_retraining_time=last_time,
        next_retraining_check=next_check,
        interaction_count=interaction_count,
        interaction_threshold=scheduler.interaction_threshold,
        retraining_interval_hours=scheduler.retraining_interval_hours
    ) 