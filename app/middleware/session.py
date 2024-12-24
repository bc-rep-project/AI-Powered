from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os

def setup_session_middleware(app: FastAPI):
    """Configure session middleware for OAuth support"""
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET_KEY", "your-super-secret-key"),
        max_age=3600  # 1 hour
    ) 