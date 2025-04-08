import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..core.config import settings
from ..db.mongodb import mongodb

logger = logging.getLogger(__name__)
router = APIRouter()

class DatasetInfo(BaseModel):
    name: str
    description: str
    num_users: int
    num_items: int
    num_interactions: int
    last_updated: Optional[datetime] = None

class DatasetResponse(BaseModel):
    success: bool
    message: str
    dataset: Optional[DatasetInfo] = None
    model_path: Optional[str] = None
    
def get_dataset_info(dataset_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve dataset information from MongoDB."""
    try:
        dataset = mongodb.datasets.find_one({"name": dataset_name})
        return dataset
    except Exception as e:
        logger.error(f"Error retrieving dataset {dataset_name}: {str(e)}")
        return None

async def train_model_task(dataset: str, epochs: int, batch_size: int) -> Dict[str, Any]:
    """Background task to train the recommendation model."""
    try:
        # Create models directory if it doesn't exist
        models_dir = Path(settings.MODEL_PATH)
        models_dir.mkdir(exist_ok=True, parents=True)
        
        # Define timestamp for model versioning
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_version_dir = models_dir / f"model_{timestamp}"
        model_version_dir.mkdir(exist_ok=True)
        
        # Build command to run training script
        script_path = Path("scripts/train_model.py")
        if not script_path.exists():
            raise FileNotFoundError(f"Training script not found at {script_path}")
        
        data_dir = Path(settings.CONTENT_PATH) / dataset
        if not data_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found at {data_dir}")
        
        cmd = [
            "python", str(script_path),
            "--data-dir", str(data_dir),
            "--model-dir", str(model_version_dir),
            "--epochs", str(epochs),
            "--batch-size", str(batch_size)
        ]
        
        logger.info(f"Running training command: {' '.join(cmd)}")
        
        # Run the training script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.returncode != 0:
            logger.error(f"Training failed: {result.stderr}")
            raise Exception(f"Model training failed: {result.stderr}")
        
        # Update the latest model symlink
        latest_symlink = models_dir / "latest"
        if latest_symlink.exists() and latest_symlink.is_symlink():
            latest_symlink.unlink()
        
        # Create relative symlink
        os.symlink(
            f"model_{timestamp}", 
            str(latest_symlink),
            target_is_directory=True
        )
        
        # Update dataset info in MongoDB
        dataset_info = await mongodb.datasets.find_one({"name": dataset})
        if dataset_info:
            await mongodb.datasets.update_one(
                {"name": dataset},
                {"$set": {"last_updated": datetime.now()}}
            )
        
        return {
            "success": True,
            "model_path": str(model_version_dir),
            "timestamp": timestamp
        }
        
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        return {"success": False, "error": str(e)}
    except subprocess.CalledProcessError as e:
        logger.error(f"Process error: {e.stderr}")
        return {"success": False, "error": e.stderr}
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/train-model", response_model=DatasetResponse)
async def train_model(
    background_tasks: BackgroundTasks,
    dataset: str = "movielens-small",
    epochs: int = 10,
    batch_size: int = 256
) -> DatasetResponse:
    """
    Train a recommendation model on the specified dataset.
    
    - **dataset**: Name of the dataset to use for training
    - **epochs**: Number of training epochs
    - **batch_size**: Batch size for training
    """
    # Check if dataset exists
    dataset_info = get_dataset_info(dataset)
    if not dataset_info:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset}' not found. Available datasets can be retrieved from /data/datasets"
        )
    
    # Add the training task to background tasks
    background_tasks.add_task(
        train_model_task,
        dataset=dataset,
        epochs=epochs,
        batch_size=batch_size
    )
    
    # Create response with dataset information
    info = DatasetInfo(
        name=dataset_info["name"],
        description=dataset_info.get("description", ""),
        num_users=dataset_info.get("num_users", 0),
        num_items=dataset_info.get("num_items", 0),
        num_interactions=dataset_info.get("num_interactions", 0),
        last_updated=dataset_info.get("last_updated")
    )
    
    return DatasetResponse(
        success=True,
        message=f"Model training started in the background for dataset '{dataset}'. Check logs for progress.",
        dataset=info,
        model_path=str(Path(settings.MODEL_PATH) / "latest")
    )

@router.get("/datasets", response_model=List[DatasetInfo])
async def list_datasets() -> List[DatasetInfo]:
    """
    Get a list of all available datasets in the system.
    """
    try:
        datasets = []
        cursor = mongodb.datasets.find({})
        async for doc in cursor:
            datasets.append(DatasetInfo(
                name=doc["name"],
                description=doc.get("description", ""),
                num_users=doc.get("num_users", 0),
                num_items=doc.get("num_items", 0),
                num_interactions=doc.get("num_interactions", 0),
                last_updated=doc.get("last_updated")
            ))
        return datasets
    except Exception as e:
        logger.error(f"Error retrieving datasets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve datasets: {str(e)}"
        )