from pydantic import BaseSettings
from typing import List

class TrainingConfig(BaseSettings):
    # Model hyperparameters
    BATCH_SIZE: int = 64
    EPOCHS: int = 10
    LEARNING_RATE: float = 0.001
    EMBEDDING_DIM: int = 128
    
    # Training settings
    MIN_INTERACTIONS: int = 5  # Minimum interactions per user/item
    VALIDATION_SPLIT: float = 0.2
    TEST_SPLIT: float = 0.1
    
    # Model architecture
    HIDDEN_LAYERS: List[int] = [256, 128, 64]
    DROPOUT_RATE: float = 0.2
    
    # Training schedule
    RETRAIN_INTERVAL_HOURS: int = 24
    MIN_NEW_INTERACTIONS: int = 100  # Minimum new interactions before retraining
    
    # Model evaluation metrics
    METRICS = ["precision@k", "recall@k", "ndcg@k"]
    K_VALUES = [5, 10, 20]
    
    # Model checkpointing
    CHECKPOINT_DIR: str = "models/checkpoints"
    BEST_MODEL_PATH: str = "models/best_model"
    
    class Config:
        env_file = ".env"

training_config = TrainingConfig() 