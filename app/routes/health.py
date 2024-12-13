from fastapi import APIRouter, HTTPException
from app.core.monitoring import metrics_logger
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        # Add your health check logic here
        return {
            "status": "healthy",
            "environment": "production",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        metrics_logger.log_error("health_check_failed", str(e))
        raise HTTPException(status_code=500, detail="Health check failed") 