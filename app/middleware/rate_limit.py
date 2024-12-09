from fastapi import FastAPI, Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging
from app.core.auth import get_current_user
from functools import wraps

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app: FastAPI):
    """Configure rate limiting for the FastAPI application"""
    
    # Add rate limiting middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        try:
            # Apply rate limiting
            await limiter.check_request(request)
            response = await call_next(request)
            return response
            
        except RateLimitExceeded as e:
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
        @limiter.limit(limit_string)
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def get_user_limit_key(request: Request):
    """Rate limit key function that considers user roles"""
    try:
        user = get_current_user(request)
        if user.is_premium:
            return f"premium_user:{user.id}"
        return f"basic_user:{user.id}"
    except:
        return get_remote_address(request)

# Different limits for different user types
RATE_LIMITS = {
    "premium_user": "1000/hour",
    "basic_user": "100/hour",
    "anonymous": "50/hour"
}

def dynamic_rate_limit(request: Request):
    """Apply different rate limits based on user type"""
    user_type = "anonymous"
    try:
        user = get_current_user(request)
        user_type = "premium_user" if user.is_premium else "basic_user"
    except:
        pass
    return RATE_LIMITS[user_type]