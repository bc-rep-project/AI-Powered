from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter()

@router.get("/")
async def health_check():
    try:
        # Add your health check logic here
        return {
            "status": "healthy",
            "environment": "production",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Health check failed") 