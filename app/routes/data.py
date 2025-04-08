from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
import json
import sys
import subprocess
import uuid
from datetime import datetime
from app.core.auth import get_current_user
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.interaction import InteractionDB, Interaction
import pandas as pd
import asyncio
import time

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])

# Models for API responses
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
    progress: Optional[float] = None
    
class ModelInfoResponse(BaseModel):
    id: str
    name: str
    version: str
    created_at: str
    performance: Dict[str, float]
    is_active: bool

# Global job tracking
active_jobs = {}

def get_dataset_status(dataset_name: str = "movielens-small") -> DatasetInfoResponse:
    """Get information about a dataset's status"""
    raw_dir = f"data/raw/{dataset_name}"
    processed_dir = f"data/processed/{dataset_name}"
    
    # Check if raw data exists
    is_downloaded = os.path.exists(raw_dir)
    
    # Check if processed data exists
    is_processed = os.path.exists(os.path.join(processed_dir, "content_items.json"))
    
    # Get more details if processed
    num_movies = 0
    num_users = 0
    num_ratings = 0
    last_processed = None
    
    if is_processed:
        try:
            # Get content items count
            with open(os.path.join(processed_dir, "content_items.json"), "r") as f:
                content_items = json.load(f)
                num_movies = len(content_items)
            
            # Get interactions count and user count
            with open(os.path.join(processed_dir, "interactions.json"), "r") as f:
                interactions = json.load(f)
                num_ratings = len(interactions)
                user_ids = set(i["user_id"] for i in interactions)
                num_users = len(user_ids)
            
            # Get last modified time of files
            last_processed = datetime.fromtimestamp(
                os.path.getmtime(os.path.join(processed_dir, "content_items.json"))
            ).isoformat()
        except Exception as e:
            logger.error(f"Error getting dataset details: {str(e)}")
    
    status = "ready" if is_processed else "not_ready"
    if not is_downloaded:
        status = "not_downloaded"
    
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
    """Run the data processor script as a background task"""
    try:
        # Create directories if they don't exist
        os.makedirs("data/raw", exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)
        
        # Build command
        cmd = [
            sys.executable,
            "scripts/data_processor.py",
            "--dataset", dataset_name,
            "--raw-dir", "data/raw",
            "--processed-dir", "data/processed"
        ]
        
        # Update job status
        active_jobs[job_id] = {
            "status": "running",
            "message": f"Downloading and processing {dataset_name} dataset",
            "progress": 0.1,
            "start_time": datetime.now().isoformat()
        }
        
        # Run process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Update progress periodically while waiting for process to complete
        while process.returncode is None:
            active_jobs[job_id]["progress"] = min(active_jobs[job_id]["progress"] + 0.1, 0.9)
            await asyncio.sleep(2)
            await process.wait()
        
        stdout, stderr = await process.communicate()
        
        # Check if process was successful
        if process.returncode == 0:
            active_jobs[job_id] = {
                "status": "completed",
                "message": f"Successfully processed {dataset_name} dataset",
                "progress": 1.0,
                "end_time": datetime.now().isoformat()
            }
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            active_jobs[job_id] = {
                "status": "failed",
                "message": f"Failed to process {dataset_name} dataset: {error_msg}",
                "progress": 1.0,
                "end_time": datetime.now().isoformat()
            }
            logger.error(f"Data processing failed: {error_msg}")
    except Exception as e:
        active_jobs[job_id] = {
            "status": "failed",
            "message": f"Error processing {dataset_name} dataset: {str(e)}",
            "progress": 1.0,
            "end_time": datetime.now().isoformat()
        }
        logger.error(f"Error in data processing task: {str(e)}")

async def run_model_trainer(dataset_name: str, job_id: str):
    """Run the model trainer script as a background task"""
    try:
        # Create directories if they don't exist
        os.makedirs("models", exist_ok=True)
        
        # Build command
        cmd = [
            sys.executable,
            "scripts/train_model.py",
            "--data-dir", f"data/processed/{dataset_name}",
            "--model-dir", "models",
            "--epochs", "10",
            "--batch-size", "64"
        ]
        
        # Update job status
        active_jobs[job_id] = {
            "status": "running",
            "message": f"Training recommendation model on {dataset_name} dataset",
            "progress": 0.1,
            "start_time": datetime.now().isoformat()
        }
        
        # Run process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Update progress periodically while waiting for process to complete
        while process.returncode is None:
            active_jobs[job_id]["progress"] = min(active_jobs[job_id]["progress"] + 0.05, 0.9)
            await asyncio.sleep(5)
            await process.wait()
        
        stdout, stderr = await process.communicate()
        
        # Check if process was successful
        if process.returncode == 0:
            # Create a symlink to latest model
            model_dirs = [d for d in os.listdir("models") if d.startswith("recommender_")]
            if model_dirs:
                latest_model = sorted(model_dirs)[-1]
                latest_link = "models/latest"
                
                # Remove existing symlink if it exists
                if os.path.exists(latest_link):
                    if os.path.islink(latest_link):
                        os.unlink(latest_link)
                    else:
                        os.rename(latest_link, f"{latest_link}_old_{int(time.time())}")
                
                # Create new symlink
                os.symlink(latest_model, latest_link)
                logger.info(f"Created symlink from {latest_model} to latest")
            
            active_jobs[job_id] = {
                "status": "completed",
                "message": f"Successfully trained model on {dataset_name} dataset",
                "progress": 1.0,
                "end_time": datetime.now().isoformat()
            }
        else:
            error_msg = stderr.decode() if stderr else "Unknown error"
            active_jobs[job_id] = {
                "status": "failed",
                "message": f"Failed to train model: {error_msg}",
                "progress": 1.0,
                "end_time": datetime.now().isoformat()
            }
            logger.error(f"Model training failed: {error_msg}")
    except Exception as e:
        active_jobs[job_id] = {
            "status": "failed",
            "message": f"Error training model: {str(e)}",
            "progress": 1.0,
            "end_time": datetime.now().isoformat()
        }
        logger.error(f"Error in model training task: {str(e)}")

# API routes
@router.get("/datasets", response_model=List[DatasetInfoResponse])
async def get_datasets(
    user = Depends(get_current_user)
):
    """Get information about available datasets"""
    try:
        # For now, we only support MovieLens datasets
        datasets = ["movielens-small", "movielens-full"]
        
        result = []
        for dataset_name in datasets:
            dataset_info = get_dataset_status(dataset_name)
            result.append(dataset_info)
        
        return result
    except Exception as e:
        logger.error(f"Error getting datasets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get datasets: {str(e)}"
        )

@router.post("/datasets/{dataset_name}/download", response_model=DataProcessingResponse)
async def download_dataset(
    dataset_name: str,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Download and process a dataset"""
    try:
        # Validate dataset name
        valid_datasets = ["movielens-small", "movielens-full"]
        if dataset_name not in valid_datasets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid dataset name. Available datasets: {valid_datasets}"
            )
        
        # Generate job ID
        job_id = f"download_{dataset_name}_{int(time.time())}"
        
        # Start background task
        background_tasks.add_task(run_data_processor, dataset_name, job_id)
        
        return DataProcessingResponse(
            status="started",
            message=f"Started downloading and processing {dataset_name} dataset",
            job_id=job_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting dataset download: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start download: {str(e)}"
        )

@router.post("/models/train", response_model=DataProcessingResponse)
async def train_model(
    dataset_name: str = "movielens-small",
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Train a recommendation model on a dataset"""
    try:
        # Check if dataset is processed
        dataset_info = get_dataset_status(dataset_name)
        if not dataset_info.is_processed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset {dataset_name} is not processed yet. Please download and process it first."
            )
        
        # Generate job ID
        job_id = f"train_model_{dataset_name}_{int(time.time())}"
        
        # Start background task
        background_tasks.add_task(run_model_trainer, dataset_name, job_id)
        
        return DataProcessingResponse(
            status="started",
            message=f"Started training model on {dataset_name} dataset",
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
        if job_id not in active_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found"
            )
        
        job_info = active_jobs[job_id]
        
        return DataProcessingResponse(
            status=job_info["status"],
            message=job_info["message"],
            job_id=job_id,
            progress=job_info.get("progress")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )

@router.get("/models", response_model=List[ModelInfoResponse])
async def get_models(
    user = Depends(get_current_user)
):
    """Get information about trained models"""
    try:
        models_dir = "models"
        if not os.path.exists(models_dir):
            return []
        
        model_dirs = [d for d in os.listdir(models_dir) if d.startswith("recommender_")]
        
        # Check what the latest model is
        latest_model = None
        if os.path.exists(os.path.join(models_dir, "latest")) and os.path.islink(os.path.join(models_dir, "latest")):
            latest_model = os.path.basename(os.readlink(os.path.join(models_dir, "latest")))
        
        result = []
        for model_dir in model_dirs:
            model_path = os.path.join(models_dir, model_dir)
            
            # Check if model_info.json exists
            info_path = os.path.join(model_path, "model_info.json")
            if not os.path.exists(info_path):
                continue
            
            # Load model info
            with open(info_path, "r") as f:
                model_info = json.load(f)
            
            # Create model info response
            model_response = ModelInfoResponse(
                id=model_dir,
                name=f"Recommendation Model {model_dir.split('_')[1]}",
                version=model_dir.split('_')[1],
                created_at=model_info.get("saved_at", datetime.fromtimestamp(os.path.getctime(model_path)).isoformat()),
                performance={
                    "embedding_dim": model_info.get("embedding_dim", 32),
                    "num_users": model_info.get("num_users", 0),
                    "num_content_items": model_info.get("num_content_items", 0)
                },
                is_active=(model_dir == latest_model)
            )
            
            result.append(model_response)
        
        # Sort by creation time (newest first)
        result.sort(key=lambda x: x.created_at, reverse=True)
        
        return result
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models: {str(e)}"
        )

@router.post("/models/{model_id}/activate", response_model=ModelInfoResponse)
async def activate_model(
    model_id: str,
    user = Depends(get_current_user)
):
    """Set a model as the active model"""
    try:
        model_path = os.path.join("models", model_id)
        
        # Check if model exists
        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model with ID {model_id} not found"
            )
        
        # Check if model_info.json exists
        info_path = os.path.join(model_path, "model_info.json")
        if not os.path.exists(info_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model with ID {model_id} is not a valid model"
            )
        
        # Create or update symlink to latest model
        latest_link = os.path.join("models", "latest")
        
        # Remove existing symlink if it exists
        if os.path.exists(latest_link):
            if os.path.islink(latest_link):
                os.unlink(latest_link)
            else:
                os.rename(latest_link, f"{latest_link}_old_{int(time.time())}")
        
        # Create new symlink
        os.symlink(model_id, latest_link)
        logger.info(f"Set model {model_id} as active model")
        
        # Load model info
        with open(info_path, "r") as f:
            model_info = json.load(f)
        
        # Create model info response
        model_response = ModelInfoResponse(
            id=model_id,
            name=f"Recommendation Model {model_id.split('_')[1]}",
            version=model_id.split('_')[1],
            created_at=model_info.get("saved_at", datetime.fromtimestamp(os.path.getctime(model_path)).isoformat()),
            performance={
                "embedding_dim": model_info.get("embedding_dim", 32),
                "num_users": model_info.get("num_users", 0),
                "num_content_items": model_info.get("num_content_items", 0)
            },
            is_active=True
        )
        
        return model_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate model: {str(e)}"
        )

@router.get("/interactions/my", response_model=List[Interaction])
async def get_my_interactions(
    limit: int = 50,
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's interactions"""
    try:
        interactions = db.query(InteractionDB).filter(
            InteractionDB.user_id == user.id
        ).limit(limit).all()
        
        result = []
        for interaction in interactions:
            result.append(Interaction(
                id=interaction.id,
                user_id=interaction.user_id,
                content_id=interaction.content_id,
                interaction_type=interaction.interaction_type,
                value=float(interaction.value) if interaction.value else None,
                timestamp=interaction.timestamp,
                metadata=interaction.interaction_metadata
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error getting user interactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interactions: {str(e)}"
        ) 