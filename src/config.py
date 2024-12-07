from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URL: str
    JWT_SECRET_KEY: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    FRONTEND_URL: str = "https://ai-powered-content-recommendation-frontend.vercel.app"

    class Config:
        env_file = ".env"

settings = Settings() 