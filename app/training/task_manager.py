import asyncio
from datetime import datetime
import time
from app.training.trainer import ModelTrainer
from app.core.training_config import training_config
from app.core.monitoring import logger, metrics_logger

class TrainingTaskManager:
    def __init__(self):
        self.trainer = ModelTrainer()
        self.is_running = False

    async def start(self):
        """Start the training task manager."""
        self.is_running = True
        logger.info("training_manager_started")
        await self._run_training_loop()

    async def stop(self):
        """Stop the training task manager."""
        self.is_running = False
        logger.info("training_manager_stopped")

    async def _run_training_loop(self):
        """Main training loop."""
        while self.is_running:
            try:
                # Train model
                logger.info("model_training_started")
                start_time = time.time()
                
                metrics = await self.trainer.train_model()
                
                if metrics:
                    duration = time.time() - start_time
                    metrics_logger.log_model_training(duration, metrics)
                    logger.info(
                        "model_training_completed",
                        duration=duration,
                        metrics=metrics
                    )
                else:
                    logger.info("model_training_skipped")
                
                # Wait for next training interval
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                metrics_logger.log_error(
                    "training_error",
                    str(e),
                    {"trainer_state": self.trainer.__dict__}
                )
                logger.error(
                    "model_training_failed",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

    def get_trainer(self) -> ModelTrainer:
        """Get the model trainer instance."""
        return self.trainer

# Global task manager instance
task_manager = TrainingTaskManager() 