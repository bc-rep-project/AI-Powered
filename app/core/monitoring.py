from pydantic_settings import BaseSettings
from typing import ClassVar, Callable
import logging
from prometheus_client import Counter, Histogram, start_http_server
import time
from functools import wraps
from fastapi import Request

class MonitoringConfig(BaseSettings):
    LOG_LEVEL: str = "INFO"
    METRICS_PORT: int = 9090
    
    # Prometheus metrics - using ClassVar to indicate these aren't settings
    REQUEST_COUNT: ClassVar[Counter] = Counter(
        'http_requests_total',
        'Total number of HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    REQUEST_LATENCY: ClassVar[Histogram] = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency in seconds',
        ['method', 'endpoint']
    )
    
    # Model metrics
    PREDICTION_COUNT: ClassVar[Counter] = Counter(
        'model_predictions_total',
        'Total number of model predictions',
        ['model_version']
    )
    
    PREDICTION_LATENCY: ClassVar[Histogram] = Histogram(
        'model_prediction_duration_seconds',
        'Model prediction latency in seconds',
        ['model_version']
    )
    
    TRAINING_DURATION: ClassVar[Histogram] = Histogram(
        'model_training_duration_seconds',
        'Model training duration in seconds',
        ['model_version']
    )
    
    class Config:
        env_file = ".env"

# Configure logging
logger = logging.getLogger("recommendation_engine")
logger.setLevel(MonitoringConfig().LOG_LEVEL)

# Configure metrics
metrics_logger = MonitoringConfig()

# Start Prometheus metrics server
try:
    start_http_server(metrics_logger.METRICS_PORT)
except Exception as e:
    logger.warning(f"Could not start metrics server: {str(e)}")

def monitor_endpoint(endpoint_name: str = None):
    """
    Decorator to monitor FastAPI endpoint performance and requests.
    
    Args:
        endpoint_name: Name of the endpoint for metrics. If None, uses the path.
    """
    def decorator(func: Callable):
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
                
            except Exception as e:
                status = "error"
                logger.error(f"Endpoint error: {str(e)}")
                raise
                
            finally:
                # Record metrics
                duration = time.time() - start_time
                
                metrics_logger.REQUEST_COUNT.labels(
                    method=method,
                    endpoint=path,
                    status=status
                ).inc()
                
                metrics_logger.REQUEST_LATENCY.labels(
                    method=method,
                    endpoint=path
                ).observe(duration)
                
                # Log request
                logger.info(
                    f"Request: {method} {path} - "
                    f"Status: {status} - "
                    f"Duration: {duration:.3f}s"
                )
            
            return response
        return wrapper
    return decorator 