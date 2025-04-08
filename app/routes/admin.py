from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..core.auth import get_current_user
from ..services.scheduler import get_scheduler
from ..services.interaction_counter import reset_interaction_counter
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

class RetrainingRequest(BaseModel):
    force: bool = False
    dataset: Optional[str] = None
    epochs: Optional[int] = None
    batch_size: Optional[int] = None

class RetrainingResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None
    timestamp: str = datetime.now().isoformat()
    details: Optional[Dict[str, Any]] = None

@router.post("/retrain-model", response_model=RetrainingResponse)
async def trigger_model_retraining(
    request: RetrainingRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """
    Manually trigger model retraining.
    
    This endpoint allows administrators to manually start the model retraining process,
    either with the default parameters or with custom parameters specified in the request.
    """
    # Get the scheduler instance
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model retraining scheduler is not available"
        )
    
    # Check if retraining is already in progress
    if hasattr(scheduler, "is_retraining") and scheduler.is_retraining:
        return RetrainingResponse(
            success=False,
            message="Another retraining job is already in progress",
            details={"status": "in_progress"}
        )
    
    # Set custom parameters if provided
    if request.dataset:
        scheduler.dataset = request.dataset
    if request.epochs:
        scheduler.epochs = request.epochs
    if request.batch_size:
        scheduler.batch_size = request.batch_size
    
    # Generate a job ID based on timestamp
    job_id = f"retrain_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Function to run the retraining in the background
    async def _run_retraining():
        try:
            # Set flag to indicate retraining is in progress
            scheduler.is_retraining = True
            
            # Perform the retraining
            result = await scheduler.retrain_model()
            
            # Reset the interaction counter regardless of success
            await reset_interaction_counter()
            
            logger.info(f"Manual retraining completed: {result}")
        except Exception as e:
            logger.error(f"Error during manual retraining: {str(e)}")
        finally:
            # Clear the retraining flag
            scheduler.is_retraining = False
    
    # Add the retraining task to background tasks
    background_tasks.add_task(_run_retraining)
    
    return RetrainingResponse(
        success=True,
        message="Model retraining started in the background",
        job_id=job_id,
        details={
            "dataset": scheduler.dataset,
            "epochs": scheduler.epochs,
            "batch_size": scheduler.batch_size
        }
    )

@router.get("/retraining-jobs/{job_id}", response_model=RetrainingResponse)
async def get_retraining_job_status(
    job_id: str,
    user = Depends(get_current_user)
):
    """
    Check the status of a retraining job.
    """
    # Get the scheduler instance
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model retraining scheduler is not available"
        )
    
    # Check if a retraining job is in progress
    is_in_progress = hasattr(scheduler, "is_retraining") and scheduler.is_retraining
    
    # In a real implementation, you would store and retrieve job details from a database
    # For this example, we'll just return the current status based on the is_retraining flag
    if is_in_progress:
        return RetrainingResponse(
            success=True,
            message="Retraining job is in progress",
            job_id=job_id,
            details={"status": "in_progress"}
        )
    else:
        # Check when the last retraining happened
        last_time = scheduler.last_retraining_time
        
        if not last_time:
            return RetrainingResponse(
                success=False,
                message="No retraining job has been completed recently",
                job_id=job_id,
                details={"status": "unknown"}
            )
        
        # If the job ID matches the format and the last retraining time is after the job ID timestamp
        try:
            job_timestamp = datetime.strptime(job_id.split("_")[1], "%Y%m%d%H%M%S")
            if last_time > job_timestamp:
                return RetrainingResponse(
                    success=True,
                    message="Retraining job completed successfully",
                    job_id=job_id,
                    details={
                        "status": "completed",
                        "completed_at": last_time.isoformat()
                    }
                )
            else:
                return RetrainingResponse(
                    success=False,
                    message="Retraining job not found or did not complete",
                    job_id=job_id,
                    details={"status": "unknown"}
                )
        except Exception:
            return RetrainingResponse(
                success=False,
                message="Invalid job ID format",
                job_id=job_id,
                details={"status": "error"}
            ) 