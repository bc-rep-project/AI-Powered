from pydantic_settings import BaseSettings
from typing import List, Optional

class TrainingConfig(BaseSettings):
    # Model Architecture
    EMBEDDING_DIM: int = 128
    HIDDEN_LAYERS: List[int] = [256, 128, 64]
    DROPOUT_RATE: float = 0.2
    ACTIVATION: str = "relu"
    
    # Training Parameters
    LEARNING_RATE: float = 0.001
    BATCH_SIZE: int = 32
    NUM_EPOCHS: int = 10
    VALIDATION_SPLIT: float = 0.2
    TEST_SPLIT: float = 0.2
    EARLY_STOPPING_PATIENCE: int = 3
    
    # Data Processing
    MAX_SEQUENCE_LENGTH: int = 100
    VOCAB_SIZE: int = 10000
    PAD_TOKEN: str = "<PAD>"
    UNK_TOKEN: str = "<UNK>"
    
    # Paths
    MODEL_CHECKPOINT_DIR: str = "models/checkpoints"
    MODEL_SAVE_PATH: str = "models/recommender"
    TENSORBOARD_LOG_DIR: str = "logs/tensorboard"
    
    # Training Resources
    USE_GPU: bool = False
    NUM_WORKERS: int = 4
    
    class Config:
        env_file = ".env"

training_config = TrainingConfig() 