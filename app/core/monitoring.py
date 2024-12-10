from prometheus_client import Counter, Histogram, Info
import logging
from functools import wraps
import time
from fastapi import Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recommendation_engine")

class MetricsLogger:
    def __init__(self):
        self.logger = logging.getLogger("api_metrics")
        
    def log_error(self, error_type: str, error_message: str, context: dict = None):
        """Log an error with context"""
        if context is None:
            context = {}
        self.logger.error(f"{error_type}: {error_message}", extra=context)
        
    def log_info(self, message: str, context: dict = None):
        """Log info with context"""
        if context is None:
            context = {}
        self.logger.info(message, extra=context)

metrics_logger = MetricsLogger()

# Metrics
REQUESTS_TOTAL = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

SYSTEM_INFO = Info('api_system', 'API system information')

def monitor_endpoint(endpoint_name: str = None):
    """
    Decorator to monitor FastAPI endpoint performance and requests.
    
    Args:
        endpoint_name: Name of the endpoint for metrics. If None, uses the path.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get endpoint name from path if not provided
            path = endpoint_name or request.url.path
            method = request.method
            
            # Start timing
            start_time = time.time()
            
            try:
                # Execute endpoint
                response = await func(request, *args, **kwargs)
                status = "success"
                return response
                
            except Exception as e:
                status = "error"
                logger.error(f"Endpoint error: {str(e)}")
                raise
                
            finally:
                # Record metrics
                duration = time.time() - start_time
                log_request(method, path, status, duration)
                
        return wrapper
    return decorator

def log_request(method: str, endpoint: str, status_code: int, duration: float):
    """Log request metrics"""
    REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status=status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)
    
    metrics_logger.log_info(
        f"Request: {method} {endpoint} {status_code} {duration:.3f}s"
    )

def set_system_info(version: str, environment: str):
    """Set system information metrics"""
    SYSTEM_INFO.info({
        'version': version,
        'environment': environment
    }) 