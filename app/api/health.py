from fastapi import APIRouter
from app.core.monitoring import get_system_metrics
from app.database import mongodb
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        # Check MongoDB
        await mongodb.db.command('ping')
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 