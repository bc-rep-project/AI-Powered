from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
import os

def setup_session_middleware(app: FastAPI) -> None:
    """Configure session middleware for the FastAPI application"""
    secret_key = os.getenv("SESSION_SECRET_KEY", "your-secret-key-here")
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="session",
        max_age=86400,  # 24 hours in seconds
        same_site="lax",
        https_only=True
    ) 