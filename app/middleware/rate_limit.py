from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from functools import wraps

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app: FastAPI):
    """Set up rate limiting for the FastAPI application"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def limit_requests(limit_string: str):
    """Decorator for rate limiting individual endpoints"""
    def decorator(func):
        @limiter.limit(limit_string)
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator