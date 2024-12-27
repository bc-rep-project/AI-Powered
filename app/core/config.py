from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Model Configuration
    ACTIVATION: str
    BATCH_SIZE: int
    DROPOUT_RATE: float
    EARLY_STOPPING_PATIENCE: int
    EMBEDDING_DIM: int
    HIDDEN_LAYERS: str  # Will be parsed from string
    LEARNING_RATE: float
    MAX_SEQUENCE_LENGTH: int
    MODEL_CHECKPOINT_DIR: str
    MODEL_NAME: str
    MODEL_SAVE_PATH: str
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None
    DB_HOST: str
    DB_NAME: str
    DB_PASSWORD: str
    DB_PORT: str
    DB_USER: str
    
    # API Configuration
    FRONTEND_URL: str
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    
    # Security and Monitoring
    HF_TOKEN: str
    JWT_ALGORITHM: str
    LOG_LEVEL: str
    METRICS_PORT: int
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 