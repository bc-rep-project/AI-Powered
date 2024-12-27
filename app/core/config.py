from pydantic import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    # Authentication
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Content Recommendation"
    
    class Config:
        env_file = ".env"

settings = Settings() 