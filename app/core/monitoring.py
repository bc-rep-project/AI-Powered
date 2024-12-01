from pydantic import BaseSettings
import logging
import json
from datetime import datetime
from typing import Any, Dict
import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    wrapper_class=structlog.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create logger
logger = structlog.get_logger()

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    "recommendation_requests_total",
    "Total number of recommendation requests",
    ["endpoint", "status"]
)

RESPONSE_TIME = Histogram(
    "recommendation_response_time_seconds",
    "Response time in seconds",
    ["endpoint"]
)

MODEL_TRAINING_TIME = Histogram(
    "model_training_time_seconds",
    "Model training time in seconds"
)

ACTIVE_USERS = Gauge(
    "active_users_total",
    "Number of active users in the last 24 hours"
)

RECOMMENDATION_QUALITY = Gauge(
    "recommendation_quality",
    "Quality metrics for recommendations",
    ["metric"]
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type"]
)

class MetricsLogger:
    """Logger for tracking various system metrics."""
    
    @staticmethod
    def log_request(endpoint: str, status: int, duration: float):
        """Log API request metrics."""
        REQUESTS_TOTAL.labels(endpoint=endpoint, status=status).inc()
        RESPONSE_TIME.labels(endpoint=endpoint).observe(duration)
        
        logger.info(
            "api_request",
            endpoint=endpoint,
            status=status,
            duration=duration
        )

    @staticmethod
    def log_model_training(duration: float, metrics: Dict[str, float]):
        """Log model training metrics."""
        MODEL_TRAINING_TIME.observe(duration)
        
        for metric, value in metrics.items():
            RECOMMENDATION_QUALITY.labels(metric=metric).set(value)
        
        logger.info(
            "model_training",
            duration=duration,
            metrics=metrics
        )

    @staticmethod
    def log_cache_operation(cache_type: str, hit: bool):
        """Log cache operation metrics."""
        if hit:
            CACHE_HITS.labels(cache_type=cache_type).inc()
        else:
            CACHE_MISSES.labels(cache_type=cache_type).inc()
        
        logger.debug(
            "cache_operation",
            cache_type=cache_type,
            hit=hit
        )

    @staticmethod
    def log_error(error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log error events."""
        logger.error(
            "error",
            error_type=error_type,
            error_message=error_message,
            context=context or {}
        )

def monitor_endpoint(endpoint_name: str):
    """Decorator for monitoring API endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                MetricsLogger.log_request(endpoint_name, 200, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                MetricsLogger.log_request(endpoint_name, 500, duration)
                MetricsLogger.log_error(
                    "endpoint_error",
                    str(e),
                    {"endpoint": endpoint_name}
                )
                raise
        return wrapper
    return decorator

# Initialize metrics logger
metrics_logger = MetricsLogger() 