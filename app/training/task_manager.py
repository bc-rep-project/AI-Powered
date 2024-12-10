import asyncio
import logging
from datetime import datetime
from app.training.trainer import ModelTrainer
from app.core.monitoring import metrics_logger

logger = logging.getLogger("recommendation_engine")

class TrainingTaskManager:
    def __init__(self):
        self.trainer = ModelTrainer()
        self.is_running = False
        
    async def start(self):
        """Start the training task manager"""
        logger.info("training_manager_started")
        self.is_running = True
        await self._run_training_loop()
        
    async def stop(self):
        """Stop the training task manager"""
        self.is_running = False
        
    async def _run_training_loop(self):
        """Main training loop"""
        while self.is_running:
            try:
                logger.info("model_training_started")
                metrics = await self.trainer.train_model()
                
                # Log training metrics
                metrics_logger.log_info(
                    "training_completed",
                    {
                        "metrics": metrics,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                # Wait before next training iteration
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                # Log error with proper context
                metrics_logger.log_error(
                    "training_error",
                    str(e),
                    {
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                await asyncio.sleep(300)  # Wait 5 minutes after error

task_manager = TrainingTaskManager() 