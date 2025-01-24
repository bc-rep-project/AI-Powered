from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, HttpUrl, validator, AnyUrl
from typing import Optional, Union, Any
import secrets

class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "AI Content Recommendation"
    
    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
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
    MONGODB_URI: Optional[str] = None
    MONGODB_DB_NAME: str = "ai_recommendation"
    
    # Redis Configuration
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        env="REDIS_URL",
        description="Full Redis connection URL including database number"
    )
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 