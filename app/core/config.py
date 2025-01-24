from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, HttpUrl, validator
from typing import Optional
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
    DATABASE_URL: Optional[PostgresDsn] = None
    DB_HOST: str = "localhost"
    DB_NAME: str = "ai_recommendation"
    DB_PASSWORD: str = ""
    DB_PORT: str = "5432"
    DB_USER: str = "postgres"
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: Optional[str], values: dict) -> str:
        if v:
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            username=values.get("DB_USER"),
            password=values.get("DB_PASSWORD"),
            host=values.get("DB_HOST"),
            port=values.get("DB_PORT"),
            path=f"/{values.get('DB_NAME')}"
        )
    
    # MongoDB Configuration
    MONGODB_URI: Optional[str] = None
    MONGODB_DB_NAME: str = "ai_recommendation"
    
    # Redis Configuration
    REDIS_URL: str = Field("redis://localhost:6379", env="REDIS_URL")
    
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