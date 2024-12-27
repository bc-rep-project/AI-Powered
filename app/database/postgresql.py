from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str = "6543"
    DB_NAME: str

    class Config:
        env_file = ".env"

settings = Settings()

DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_database_connection():
    """Test the database connection by executing a simple query"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False 