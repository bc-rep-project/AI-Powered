from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
from pydantic import validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Content Recommendation Engine"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = None
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if v is not None:
            return v
        
        return f"postgresql://postgres:{values['SUPABASE_JWT_SECRET']}@db.{values['SUPABASE_URL']}.supabase.co:5432/postgres"
    
    # Auth
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Model
    HF_TOKEN: str
    MODEL_NAME: str = "sentence-transformers/all-mpnet-base-v2"
    
    # Service URLs
    FRONTEND_URL: str
    API_URL: Optional[str] = None
    
    # Redis Configuration
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_CACHE_TTL: int = 86400  # 24 hours in seconds
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v
    
    class Config:
        env_file = ".env"

settings = Settings() 