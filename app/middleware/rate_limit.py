from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("5/minute")
async def rate_limit_middleware(request: Request):
    pass

def setup_rate_limiting(app: FastAPI):
    """Configure rate limiting for the FastAPI application"""
    app.state.limiter = limiter
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        try:
            # Get the endpoint handler
            endpoint = request.scope.get("endpoint", None)
            if endpoint and hasattr(endpoint, "_rate_limit"):
                await limiter.hit(request)
            
            response = await call_next(request)
            return response
            
        except RateLimitExceeded:
            logger.warning(f"Rate limit exceeded for {get_remote_address(request)}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            return await call_next(request)

def limit_requests(limit_string: str):
    """Decorator for rate limiting individual endpoints"""
    def decorator(func):
        setattr(func, "_rate_limit", limit_string)
        return limiter.limit(limit_string)(func)
    return decorator