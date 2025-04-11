"""
Dedicated training endpoint for model training.
This separate implementation avoids issues with the dataset router.
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from pydantic import BaseModel

from ..core.config import settings
from ..core.auth import get_current_user
from ..routes.dataset import train_model_task
from ..db.mongodb import mongodb

logger = logging.getLogger(__name__)
router = APIRouter()

class TrainingRequest(BaseModel):
    dataset: str = "movielens-small"
    epochs: int = 5
    batch_size: int = 32
    lightweight: bool = True

class TrainingResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None
    status: str = "pending"

@router.post("/model-training", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """
    Train a recommendation model on the specified dataset.
    
    This endpoint bypasses the issues with the original train-model endpoint.
    """
    try:
        # Check if dataset exists
        dataset_info = None
        try:
            dataset_info = await mongodb.datasets.find_one({"name": request.dataset})
        except Exception as db_err:
            logger.warning(f"Error checking dataset: {str(db_err)}")
            
        if not dataset_info:
            # Try local filesystem check
            data_dir = Path(settings.CONTENT_PATH) / request.dataset
            if not data_dir.exists():
                # Try alternative path
                alt_data_dir = Path("data/processed") / request.dataset
                if not alt_data_dir.exists():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Dataset '{request.dataset}' not found. Please download it first."
                    )
        
        # Import job queue if available
        try:
            from ..services.job_queue import create_job, execute_job
            
            # Create a job for model training
            job_id = await create_job("train_model", {
                "dataset": request.dataset,
                "epochs": request.epochs,
                "batch_size": request.batch_size
            })
            
            # Execute in background
            background_tasks.add_task(execute_job, job_id, train_model_task)
            
            return TrainingResponse(
                success=True,
                message=f"Model training started with job ID: {job_id}. "
                        f"Check status at /api/v1/data/jobs/{job_id}",
                job_id=job_id,
                status="pending"
            )
        except ImportError:
            # Fall back to direct execution
            logger.info("Job queue not available, falling back to direct training execution")
            
            # Generate a simple job ID
            job_id = f"train_{int(datetime.now().timestamp())}"
            
            # Store job info in a file
            jobs_dir = Path("data/jobs")
            jobs_dir.mkdir(exist_ok=True, parents=True)
            job_file = jobs_dir / f"{job_id}.json"
            
            job_data = {
                "job_id": job_id,
                "status": "pending",
                "message": "Job created and scheduled",
                "progress": 0.0,
                "created_at": datetime.now().isoformat(),
                "parameters": {
                    "dataset": request.dataset,
                    "epochs": request.epochs,
                    "batch_size": request.batch_size
                }
            }
            
            with open(job_file, "w") as f:
                json.dump(job_data, f)
            
            # Execute in background
            background_tasks.add_task(
                train_model_task,
                dataset=request.dataset,
                epochs=request.epochs,
                batch_size=request.batch_size
            )
            
            return TrainingResponse(
                success=True,
                message=f"Model training started with job ID: {job_id}. "
                        f"Check status at /api/v1/data/jobs/{job_id}",
                job_id=job_id,
                status="pending"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting model training: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start model training: {str(e)}"
        ) 