from fastapi import Request
import logging

async def log_request(request: Request, call_next):
    logger = logging.getLogger("api")
    logger.info(f"{request.method} {request.url}")
    
    try:
        response = await call_next(request)
        logger.info(f"Status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise 