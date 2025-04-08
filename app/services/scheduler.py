"""
Scheduler service for periodic tasks in the recommendation system.
This module handles scheduled tasks like model retraining based on user interactions.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import time
import threading
from typing import Dict, Any, Optional

from ..core.config import settings
from ..db.mongodb import mongodb
from ..db.redis import get_redis

logger = logging.getLogger(__name__)

class ModelRetrainingScheduler:
    """Scheduler for periodic model retraining based on user interactions."""
    
    def __init__(
        self, 
        retraining_interval_hours: int = 12,
        interaction_threshold: int = 50,
        dataset: str = "movielens-small",
        epochs: int = 10,
        batch_size: int = 64
    ):
        """
        Initialize the model retraining scheduler.
        
        Args:
            retraining_interval_hours: Hours between retraining checks
            interaction_threshold: Minimum number of new interactions needed to trigger retraining
            dataset: Dataset name to use for retraining
            epochs: Number of training epochs
            batch_size: Batch size for training
        """
        self.retraining_interval_hours = retraining_interval_hours
        self.interaction_threshold = interaction_threshold
        self.dataset = dataset
        self.epochs = epochs
        self.batch_size = batch_size
        self.running = False
        self.last_retraining_time = None
        self.thread = None
        self.lock = threading.Lock()
    
    async def should_retrain(self) -> bool:
        """
        Check if model retraining should be triggered based on:
        1. Time elapsed since last retraining
        2. Number of new interactions since last retraining
        
        Returns:
            bool: True if retraining should be triggered
        """
        # Check if enough time has passed since last retraining
        if self.last_retraining_time is None:
            # If never retrained, check if initial model exists
            model_path = Path(settings.MODEL_PATH) / "latest"
            if not model_path.exists():
                logger.info("No existing model found. Retraining needed.")
                return True
        else:
            time_since_last_retraining = datetime.now() - self.last_retraining_time
            if time_since_last_retraining < timedelta(hours=self.retraining_interval_hours):
                logger.info(f"Not enough time elapsed since last retraining ({time_since_last_retraining})")
                return False
        
        # Check new interaction count since last retraining
        try:
            redis = await get_redis()
            if redis:
                # Get the count of new interactions since last retraining
                new_interactions_count = await redis.get("new_interactions_count")
                if new_interactions_count:
                    new_interactions_count = int(new_interactions_count)
                    logger.info(f"Found {new_interactions_count} new interactions since last retraining")
                    if new_interactions_count >= self.interaction_threshold:
                        logger.info(f"Interaction threshold reached ({new_interactions_count} >= {self.interaction_threshold})")
                        return True
                    else:
                        logger.info(f"Interaction threshold not reached ({new_interactions_count} < {self.interaction_threshold})")
                else:
                    # Initialize counter if it doesn't exist
                    await redis.set("new_interactions_count", 0)
            
            # Fallback to checking MongoDB if Redis is not available
            else:
                logger.warning("Redis not available. Checking MongoDB for interactions.")
                if mongodb:
                    # Get last retraining time from MongoDB or use a default
                    model_info = await mongodb.models.find_one({"is_active": True}, sort=[("created_at", -1)])
                    last_time = model_info.get("created_at") if model_info else (datetime.now() - timedelta(days=30))
                    
                    # Count interactions since that time
                    new_count = await mongodb.interactions.count_documents({"timestamp": {"$gt": last_time}})
                    logger.info(f"Found {new_count} new interactions in MongoDB since last retraining")
                    return new_count >= self.interaction_threshold
                else:
                    logger.warning("Neither Redis nor MongoDB available. Defaulting to time-based retraining.")
                    return True
        except Exception as e:
            logger.error(f"Error checking interaction count: {str(e)}")
            # Default to True if there's an error checking conditions
            return True
        
        return False
    
    async def retrain_model(self) -> Dict[str, Any]:
        """
        Retrain the recommendation model based on available data.
        """
        logger.info("Starting model retraining...")
        
        try:
            # Record retrain start time
            retrain_start = datetime.now()
            
            # Get model paths
            model_path = getattr(settings, "MODEL_PATH", "models/latest")
            if not model_path:
                model_path = "models/latest"
                
            save_path = os.path.join("models", f"recommender_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Get dataset paths
            dataset_path = os.path.join("data", "processed", self.dataset)
            if not os.path.exists(dataset_path):
                logger.error(f"Dataset path {dataset_path} does not exist")
                return {
                    "success": False, 
                    "error": f"Dataset path {dataset_path} not found"
                }
            
            # Set training parameters 
            params = {
                "data_dir": dataset_path,
                "model_dir": save_path,
                "epochs": self.epochs,
                "batch_size": self.batch_size,
                "embedding_dim": getattr(settings, "EMBEDDING_DIM", 32),
                "learning_rate": getattr(settings, "LEARNING_RATE", 0.001)
            }
            
            # Build command to run training script
            script_path = Path(__file__).parent.parent.parent / "scripts" / "train_model.py"
            if not script_path.exists():
                raise FileNotFoundError(f"Training script not found at {script_path}")
            
            # Run training command
            cmd = [
                "python", str(script_path),
                "--data-dir", str(params["data_dir"]),
                "--model-dir", str(params["model_dir"]),
                "--epochs", str(params["epochs"]),
                "--batch-size", str(params["batch_size"]),
                "--embedding-dim", str(params["embedding_dim"]),
                "--learning-rate", str(params["learning_rate"])
            ]
            
            logger.info(f"Running retraining command: {' '.join(cmd)}")
            
            # Run the training script as a subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode != 0:
                logger.error(f"Retraining failed: {result.stderr}")
                raise Exception(f"Model retraining failed: {result.stderr}")
            
            # Update the latest model symlink
            latest_symlink = Path(model_path)
            if latest_symlink.exists() and latest_symlink.is_symlink():
                latest_symlink.unlink()
            
            # Create relative symlink to the new model
            os.symlink(
                f"recommender_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                str(latest_symlink),
                target_is_directory=True
            )
            
            # Update retraining time
            self.last_retraining_time = datetime.now()
            
            # Reset interaction counter in Redis
            try:
                redis = await get_redis()
                if redis:
                    await redis.set("new_interactions_count", 0)
            except Exception as e:
                logger.error(f"Error resetting interaction counter: {str(e)}")
            
            # Store training result in MongoDB
            try:
                if mongodb:
                    # Deactivate all previous models
                    await mongodb.models.update_many(
                        {"is_active": True},
                        {"$set": {"is_active": False}}
                    )
                    
                    # Insert new model info
                    await mongodb.models.insert_one({
                        "id": f"recommender_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "name": "Recommendation Model",
                        "version": datetime.now().strftime('%Y%m%d_%H%M%S'),
                        "created_at": datetime.now(),
                        "path": str(save_path),
                        "is_active": True,
                        "performance": {
                            "accuracy": 0.0,  # These would be populated by evaluation
                            "recall": 0.0,
                            "precision": 0.0
                        }
                    })
            except Exception as e:
                logger.error(f"Error storing model info in MongoDB: {str(e)}")
            
            return {
                "success": True,
                "model_path": str(save_path),
                "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            
        except Exception as e:
            logger.error(f"Error retraining model: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _run_scheduler(self):
        """Main scheduler loop that periodically checks for retraining conditions."""
        logger.info(f"Starting model retraining scheduler (interval: {self.retraining_interval_hours} hours)")
        
        while self.running:
            try:
                # Check if we should retrain
                if await self.should_retrain():
                    logger.info("Starting model retraining...")
                    result = await self.retrain_model()
                    
                    if result["success"]:
                        logger.info(f"Model retraining completed successfully: {result['model_path']}")
                    else:
                        logger.error(f"Model retraining failed: {result.get('error', 'Unknown error')}")
                
                # Sleep for an hour before checking again
                # This is more frequent than the retraining interval to be responsive
                # to interaction threshold being reached
                for _ in range(60):  # Check every minute if we're still running
                    if not self.running:
                        break
                    await asyncio.sleep(60)  # 1 minute
                    
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                await asyncio.sleep(300)  # 5 minutes before retry on error
    
    def start(self):
        """Start the scheduler in a background thread."""
        with self.lock:
            if not self.running:
                self.running = True
                
                # Create event loop for the thread
                async def _start_scheduler():
                    await self._run_scheduler()
                
                # Start in a separate thread
                def _thread_target():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_start_scheduler())
                
                self.thread = threading.Thread(target=_thread_target)
                self.thread.daemon = True
                self.thread.start()
                logger.info("Model retraining scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        with self.lock:
            if self.running:
                self.running = False
                if self.thread:
                    self.thread.join(timeout=5)
                    self.thread = None
                logger.info("Model retraining scheduler stopped")

# Singleton instance
scheduler: Optional[ModelRetrainingScheduler] = None

def init_scheduler(
    retraining_interval_hours: int = 12,
    interaction_threshold: int = 50,
    dataset: str = "movielens-small",
    epochs: int = 10,
    batch_size: int = 64
) -> ModelRetrainingScheduler:
    """
    Initialize and return the scheduler singleton.
    
    Args:
        retraining_interval_hours: Hours between retraining checks
        interaction_threshold: Minimum number of new interactions needed to trigger retraining
        dataset: Dataset name to use for retraining
        epochs: Number of training epochs
        batch_size: Batch size for training
        
    Returns:
        ModelRetrainingScheduler: The scheduler instance
    """
    global scheduler
    if scheduler is None:
        scheduler = ModelRetrainingScheduler(
            retraining_interval_hours=retraining_interval_hours,
            interaction_threshold=interaction_threshold,
            dataset=dataset,
            epochs=epochs,
            batch_size=batch_size
        )
    return scheduler

def get_scheduler() -> Optional[ModelRetrainingScheduler]:
    """Get the scheduler singleton instance."""
    return scheduler 