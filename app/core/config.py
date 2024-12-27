from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "AI Content Recommendation"
    
    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model Configuration
    ACTIVATION: str = "relu"  # Default activation function
    BATCH_SIZE: int = 32
    DROPOUT_RATE: float = 0.2
    EARLY_STOPPING_PATIENCE: int = 5
    EMBEDDING_DIM: int = 128
    HIDDEN_LAYERS: str = "[256, 128, 64]"  # Will be parsed from string
    LEARNING_RATE: float = 0.001
    MAX_SEQUENCE_LENGTH: int = 100
    MODEL_CHECKPOINT_DIR: str = "checkpoints"
    MODEL_NAME: str = "recommendation_model"
    MODEL_SAVE_PATH: str = "models"
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None
    DB_HOST: str
    DB_NAME: str
    DB_PASSWORD: str
    DB_PORT: str
    DB_USER: str
    
    # MongoDB Configuration
    MONGODB_URI: Optional[str] = None
    MONGODB_DB_NAME: str = "ai_recommendation"
    
    # Redis Configuration (all optional with defaults)
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = 6379
    REDIS_DB: Optional[int] = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # API Configuration
    API_V1_STR: str = "/api/v1"  # Default value for API prefix
    FRONTEND_URL: str = "http://localhost:3000"  # Default frontend URL
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # Security and Monitoring
    HF_TOKEN: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    LOG_LEVEL: str = "INFO"
    METRICS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 