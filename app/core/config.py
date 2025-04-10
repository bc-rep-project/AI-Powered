import sys
import logging
import subprocess
import os

# Try to import pydantic_settings
try:
    from pydantic_settings import BaseSettings
except ImportError:
    logging.warning("pydantic-settings not found. Attempting to install it...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pydantic-settings>=2.0.0"])
    from pydantic_settings import BaseSettings

from pydantic import Field, PostgresDsn, HttpUrl, validator, AnyUrl
from typing import Optional, Union, Any, List, Dict
import secrets

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "AI Content Recommendation"
    
    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Resource Constraints for Free Tier
    MAX_MEMORY_PERCENT: int = Field(75, env="MAX_MEMORY_PERCENT")
    MAX_CPU_PERCENT: int = Field(70, env="MAX_CPU_PERCENT")
    FREE_TIER_MODE: bool = Field(True, env="FREE_TIER_MODE")
    WORKER_TIMEOUT: int = Field(120, env="WORKER_TIMEOUT")
    REQUEST_TIMEOUT: int = Field(30, env="REQUEST_TIMEOUT")
    BACKGROUND_WORKER_COUNT: int = Field(1, env="BACKGROUND_WORKER_COUNT")
    ENABLE_MEMORY_OPTIMIZATION: bool = Field(True, env="ENABLE_MEMORY_OPTIMIZATION")
    GC_THRESHOLD: int = Field(70, env="GC_THRESHOLD")
    OFFLOAD_TO_MONGODB: bool = Field(True, env="OFFLOAD_TO_MONGODB")
    OFFLOAD_TO_SUPABASE: bool = Field(True, env="OFFLOAD_TO_SUPABASE")
    
    # Dataset Configuration
    DATASET_SIZE: str = Field("small", env="DATASET_SIZE")
    MAX_INTERACTIONS_LOAD: int = Field(10000, env="MAX_INTERACTIONS_LOAD")
    SAMPLE_RATIO: float = Field(0.1, env="SAMPLE_RATIO")
    MAX_CONTENT_ITEMS: int = Field(1000, env="MAX_CONTENT_ITEMS")
    ENABLE_DATA_CACHING: bool = Field(True, env="ENABLE_DATA_CACHING")
    DATA_PROCESSING_CHUNK_SIZE: int = Field(1000, env="DATA_PROCESSING_CHUNK_SIZE")
    DATA_PROCESSING_SLEEP_SEC: int = Field(2, env="DATA_PROCESSING_SLEEP_SEC")
    DOWNLOAD_RETRY_COUNT: int = Field(3, env="DOWNLOAD_RETRY_COUNT")
    DOWNLOAD_TIMEOUT: int = Field(300, env="DOWNLOAD_TIMEOUT")
    
    # API Configuration
    API_RATE_LIMIT: str = Field("60/minute", env="API_RATE_LIMIT")
    API_TIMEOUT: int = Field(30, env="API_TIMEOUT")
    
    # Database Configuration - Connection Pooling
    DB_POOL_SIZE: int = Field(3, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(5, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(1800, env="DB_POOL_RECYCLE")
    
    # Redis Configuration
    REDIS_MAX_CONNECTIONS: int = Field(5, env="REDIS_MAX_CONNECTIONS")
    REDIS_TIMEOUT: int = Field(5, env="REDIS_TIMEOUT")
    REDIS_CACHE_TTL: int = Field(3600, env="REDIS_CACHE_TTL")
    
    # MongoDB Configuration
    MONGODB_POOL_SIZE: int = Field(5, env="MONGODB_POOL_SIZE")
    MONGODB_CONNECT_TIMEOUT_MS: int = Field(5000, env="MONGODB_CONNECT_TIMEOUT_MS")
    MONGODB_SOCKET_TIMEOUT_MS: int = Field(10000, env="MONGODB_SOCKET_TIMEOUT_MS")
    
    # Model Configuration
    ACTIVATION: str = "relu"  # Default activation function
    BATCH_SIZE: int = 8
    DROPOUT_RATE: float = 0.2
    EARLY_STOPPING_PATIENCE: int = 2
    EMBEDDING_DIM: int = 16
    HIDDEN_LAYERS: str = "[32, 16]"  # Will be parsed from string
    LEARNING_RATE: float = 0.001
    MAX_SEQUENCE_LENGTH: int = 50
    MODEL_CHECKPOINT_DIR: str = "checkpoints"
    MODEL_NAME: str = "distilbert-base-uncased"
    MODEL_SAVE_PATH: str = "models"
    VOCAB_SIZE: int = 5000
    
    # Model Retraining Settings
    MODEL_RETRAINING_INTERVAL_HOURS: int = Field(
        72,
        env="MODEL_RETRAINING_INTERVAL_HOURS",
        description="Hours between model retraining checks"
    )
    MODEL_RETRAINING_INTERACTION_THRESHOLD: int = Field(
        200,
        env="MODEL_RETRAINING_INTERACTION_THRESHOLD",
        description="Minimum number of new interactions needed to trigger retraining"
    )
    MODEL_RETRAINING_MAX_RUNTIME: int = Field(
        900,
        env="MODEL_RETRAINING_MAX_RUNTIME",
        description="Maximum runtime in seconds for model retraining"
    )
    ENABLE_AUTO_RETRAINING: bool = Field(
        True,
        env="ENABLE_AUTO_RETRAINING",
        description="Whether to enable automatic retraining"
    )
    RETRAINING_TIME_WINDOW_START: int = Field(
        2,
        env="RETRAINING_TIME_WINDOW_START",
        description="Start hour (0-23) of the retraining time window"
    )
    RETRAINING_TIME_WINDOW_END: int = Field(
        5,
        env="RETRAINING_TIME_WINDOW_END",
        description="End hour (0-23) of the retraining time window"
    )
    LIGHTWEIGHT_TRAINING_MODE: bool = Field(
        True,
        env="LIGHTWEIGHT_TRAINING_MODE",
        description="Use lighter, faster training methods for free tier"
    )
    
    # Database Configuration
    DATABASE_URL: Optional[Union[PostgresDsn, str]] = None
    DB_HOST: str = "localhost"
    DB_NAME: str = "ai_recommendation"
    DB_PASSWORD: str = ""
    DB_PORT: str = "5432"
    DB_USER: str = "postgres"
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str], values: dict) -> Any:
        if isinstance(v, str):
            return v
        if v is None:
            required_fields = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
            missing_fields = [field for field in required_fields if not values.get(field)]
            if missing_fields:
                return None
                
            return f"postgresql://{values.get('DB_USER')}:{values.get('DB_PASSWORD')}@{values.get('DB_HOST')}:{values.get('DB_PORT')}/{values.get('DB_NAME')}"
        return v
    
    # MongoDB Configuration
    MONGODB_URI: str = Field(
        "mongodb://localhost:27017",
        env="MONGODB_URI",
        description="MongoDB connection string"
    )
    MONGODB_DB_NAME: str = Field(
        "ai_recommendation",
        env="MONGODB_DB_NAME",
        description="MongoDB database name"
    )
    
    @validator("MONGODB_URI")
    def validate_mongodb_uri(cls, v):
        if not v.startswith("mongodb://") and not v.startswith("mongodb+srv://"):
            raise ValueError("MongoDB URI must start with mongodb:// or mongodb+srv://")
        return v
    
    # Redis Configuration
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        env="REDIS_URL",
        description="Full Redis connection URL including credentials"
    )
    # Add individual Redis connection parameters
    REDIS_HOST: str = Field(
        "localhost",
        env="REDIS_HOST",
        description="Redis host address"
    )
    REDIS_PORT: int = Field(
        6379,
        env="REDIS_PORT",
        description="Redis port number"
    )
    REDIS_PASSWORD: Optional[str] = Field(
        None,
        env="REDIS_PASSWORD",
        description="Redis password"
    )
    REDIS_DB: int = Field(
        0,
        env="REDIS_DB",
        description="Redis database number"
    )
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    FRONTEND_URL: str = Field(
        "https://ai-powered-content-recommendation-frontend.vercel.app",
        env="FRONTEND_URL",
        description="Frontend application URL"
    )
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # Security and Monitoring
    HF_TOKEN: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    LOG_LEVEL: str = "INFO"
    METRICS_PORT: int = 9090
    
    # Model Service
    MODEL_SERVICE_URL: Optional[HttpUrl] = Field(
        "http://localhost:8500",
        env="MODEL_SERVICE_URL",
        description="URL for the TensorFlow Serving model service"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        min_length=32,
        env="SECRET_KEY"
    )
    ALGORITHM: str = "HS256"
    TOKEN_DEBUG: bool = Field(False, env="TOKEN_DEBUG")
    
    # Wikipedia Configuration
    WIKI_CACHE_TTL: int = Field(
        3600,
        env="WIKI_CACHE_TTL",
        description="Wikipedia cache time-to-live in seconds"
    )
    
    class Config:
        # Set env_file only if it exists to avoid warnings
        env_file = ".env" if os.path.isfile(".env") else None
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Make the .env file optional to avoid warnings in production
        extra = "ignore"  
        validate_assignment = True

settings = Settings()