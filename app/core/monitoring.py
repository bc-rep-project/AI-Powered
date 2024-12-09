from prometheus_client import Counter, Histogram, Info
import logging

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

# Logger setup
logging.basicConfig(level=logging.INFO)
metrics_logger = logging.getLogger("api_metrics")

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
    
    metrics_logger.info(
        f"Request: {method} {endpoint} {status_code} {duration:.3f}s"
    )

def set_system_info(version: str, environment: str):
    """Set system information metrics"""
    SYSTEM_INFO.info({
        'version': version,
        'environment': environment
    }) 