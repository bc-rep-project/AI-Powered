from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
import sys
import json
import subprocess
from ..core.auth import get_current_user
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])

# Path to scripts and data
SCRIPTS_PATH = "scripts"
DATA_RAW_PATH = "data/raw"
DATA_PROCESSED_PATH = "data/processed"
MODELS_PATH = "models"

# Models for responses
class DatasetInfoResponse(BaseModel):
    name: str
    status: str
    num_movies: int = 0
    num_users: int = 0
    num_ratings: int = 0
    last_processed: Optional[str] = None
    is_downloaded: bool = False
    is_processed: bool = False

class DataProcessingResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None

# Global storage for job statuses
processing_jobs = {}

def get_dataset_status(dataset_name: str = "movielens-small") -> DatasetInfoResponse:
    """Get the status of a dataset"""
    raw_path = os.path.join(DATA_RAW_PATH, dataset_name)
    processed_path = os.path.join(DATA_PROCESSED_PATH, dataset_name)
    
    is_downloaded = os.path.exists(raw_path) and len(os.listdir(raw_path)) > 0
    is_processed = os.path.exists(processed_path) and len(os.listdir(processed_path)) > 0
    
    num_movies = 0
    num_users = 0
    num_ratings = 0
    last_processed = None
    
    if is_processed:
        try:
            # Try to load content_items.json
            content_path = os.path.join(processed_path, 'content_items.json')
            if os.path.exists(content_path):
                with open(content_path, 'r') as f:
                    content_items = json.load(f)
                    num_movies = len(content_items)
            
            # Try to load interactions.json
            interactions_path = os.path.join(processed_path, 'interactions.json')
            if os.path.exists(interactions_path):
                with open(interactions_path, 'r') as f:
                    interactions = json.load(f)
                    num_ratings = len(interactions)
                    # Get unique user IDs
                    user_ids = set(item.get('user_id') for item in interactions)
                    num_users = len(user_ids)
            
            # Get last processed timestamp
            if os.path.exists(processed_path):
                stats = os.stat(processed_path)
                last_processed = datetime.fromtimestamp(stats.st_mtime).isoformat()
        except Exception as e:
            logger.error(f"Error getting dataset stats: {str(e)}")
    
    status = "not_started"
    if is_downloaded:
        status = "downloaded"
    if is_processed:
        status = "processed"
    
    return DatasetInfoResponse(
        name=dataset_name,
        status=status,
        num_movies=num_movies,
        num_users=num_users,
        num_ratings=num_ratings,
        last_processed=last_processed,
        is_downloaded=is_downloaded,
        is_processed=is_processed
    )

async def run_data_processor(dataset_name: str, job_id: str):
    """Run the data_processor.py script as a background task"""
    try:
        # Update job status
        processing_jobs[job_id] = {"status": "running", "message": "Starting data processor..."}
        
        # Run the data_processor.py script
        cmd = [
            sys.executable,
            os.path.join(SCRIPTS_PATH, "data_processor.py"),
            "--dataset", dataset_name,
            "--raw-dir", DATA_RAW_PATH,
            "--processed-dir", DATA_PROCESSED_PATH
        ]
        
        # Execute command and capture output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Check if the process was successful
        if process.returncode == 0:
            processing_jobs[job_id] = {
                "status": "completed", 
                "message": "Data processing completed successfully",
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
        else:
            processing_jobs[job_id] = {
                "status": "failed", 
                "message": f"Data processing failed with code {process.returncode}",
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
    except Exception as e:
        logger.error(f"Error running data processor: {str(e)}")
        processing_jobs[job_id] = {"status": "failed", "message": str(e)}

async def run_model_trainer(dataset_name: str, job_id: str):
    """Run the train_model.py script as a background task"""
    try:
        # Update job status
        processing_jobs[job_id] = {"status": "running", "message": "Starting model trainer..."}
        
        # Run the train_model.py script
        cmd = [
            sys.executable,
            os.path.join(SCRIPTS_PATH, "train_model.py"),
            "--data-dir", os.path.join(DATA_PROCESSED_PATH, dataset_name),
            "--model-dir", MODELS_PATH,
            "--epochs", "5",
            "--batch-size", "64"
        ]
        
        # Execute command and capture output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Check if the process was successful
        if process.returncode == 0:
            # Create symlink to latest model
            latest_model_dir = None
            for item in os.listdir(MODELS_PATH):
                if item.startswith("recommender_") and os.path.isdir(os.path.join(MODELS_PATH, item)):
                    if latest_model_dir is None or item > latest_model_dir:
                        latest_model_dir = item
            
            if latest_model_dir:
                latest_link = os.path.join(MODELS_PATH, "latest")
                if os.path.exists(latest_link):
                    os.remove(latest_link)
                os.symlink(latest_model_dir, latest_link)
                
            processing_jobs[job_id] = {
                "status": "completed", 
                "message": "Model training completed successfully",
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
        else:
            processing_jobs[job_id] = {
                "status": "failed", 
                "message": f"Model training failed with code {process.returncode}",
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
    except Exception as e:
        logger.error(f"Error running model trainer: {str(e)}")
        processing_jobs[job_id] = {"status": "failed", "message": str(e)}

@router.get("/datasets", response_model=List[DatasetInfoResponse])
async def get_datasets(
    user = Depends(get_current_user)
):
    """Get a list of available datasets and their status"""
    try:
        # Currently we only support movielens-small and movielens-full
        datasets = ["movielens-small", "movielens-full"]
        
        result = []
        for dataset in datasets:
            result.append(get_dataset_status(dataset))
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving datasets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve datasets: {str(e)}"
        )

@router.post("/datasets/{dataset_name}/download", response_model=DataProcessingResponse)
async def download_dataset(
    dataset_name: str,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Download and process a dataset"""
    try:
        # Check if the dataset name is valid
        if dataset_name not in ["movielens-small", "movielens-full"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid dataset name: {dataset_name}"
            )
        
        # Generate a job ID
        job_id = f"download_{dataset_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Start the data processor in the background
        background_tasks.add_task(run_data_processor, dataset_name, job_id)
        
        return DataProcessingResponse(
            status="started",
            message=f"Started downloading and processing {dataset_name}",
            job_id=job_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting dataset download: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start dataset download: {str(e)}"
        )

@router.post("/models/train", response_model=DataProcessingResponse)
async def train_model(
    dataset_name: str = "movielens-small",
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Train a recommendation model on the processed dataset"""
    try:
        # Check if the dataset has been processed
        dataset_status = get_dataset_status(dataset_name)
        if not dataset_status.is_processed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset {dataset_name} has not been processed yet"
            )
        
        # Generate a job ID
        job_id = f"train_{dataset_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Start the model trainer in the background
        background_tasks.add_task(run_model_trainer, dataset_name, job_id)
        
        return DataProcessingResponse(
            status="started",
            message=f"Started training model on {dataset_name}",
            job_id=job_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting model training: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start model training: {str(e)}"
        )

@router.get("/jobs/{job_id}", response_model=DataProcessingResponse)
async def get_job_status(
    job_id: str,
    user = Depends(get_current_user)
):
    """Get the status of a background job"""
    try:
        job = processing_jobs.get(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found"
            )
        
        return DataProcessingResponse(
            status=job.get("status", "unknown"),
            message=job.get("message", "No status available"),
            job_id=job_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job status: {str(e)}"
        ) 