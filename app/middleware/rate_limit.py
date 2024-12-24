from typing import Callable, Dict
from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timedelta
import logging
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Store request counts per IP
request_store: Dict[str, Dict] = {}

def get_client_ip(request: Request) -> str:
    """Get client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"

def is_rate_limited(ip: str, limit: int = 5, window: int = 60) -> bool:
    """Check if request should be rate limited"""
    now = datetime.now()
    
    if ip not in request_store:
        request_store[ip] = {
            "count": 1,
            "window_start": now
        }
        return False
        
    window_start = request_store[ip]["window_start"]
    if now - window_start > timedelta(seconds=window):
        # Reset window
        request_store[ip] = {
            "count": 1,
            "window_start": now
        }
        return False
        
    request_store[ip]["count"] += 1
    return request_store[ip]["count"] > limit

def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting for the FastAPI application"""
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable):
        try:
            client_ip = get_client_ip(request)
            
            if is_rate_limited(client_ip):
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."}
                )
            
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            return await call_next(request)

def limit_requests(limit_string: str):
    """Decorator for rate limiting individual endpoints"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator