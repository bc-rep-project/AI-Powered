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
        description="Redis connection URL (redis://user:password@host:port/db)"
    )
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return "redis://{host}:{port}/{db}".format(
            host=values.get("REDIS_HOST", "localhost"),
            port=values.get("REDIS_PORT", "6379"),
            db=values.get("REDIS_DB", "0")
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
    
    # Wikipedia Configuration
    WIKI_CACHE_TTL: int = Field(
        3600,
        env="WIKI_CACHE_TTL",
        description="Wikipedia cache time-to-live in seconds"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()