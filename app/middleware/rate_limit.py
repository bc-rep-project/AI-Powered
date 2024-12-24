from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

def limit_requests(limit_string: str):
    """
    Decorator for rate limiting endpoints
    Example usage: @limit_requests("5/minute")
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if request:
                # Get client IP
                client_ip = get_remote_address(request)
                
                # Check rate limit
                if not limiter.test(client_ip, limit_string):
                    raise HTTPException(
                        status_code=429,
                        detail="Too many requests"
                    )
                    
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Add this function that was missing
def setup_rate_limiting(app):
    """
    Configure rate limiting for the FastAPI app
    """
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Add limiter instance to request state
        request.state.limiter = limiter
        response = await call_next(request)
        return response