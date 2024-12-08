from pydantic_settings import BaseSettings
import logging
from prometheus_client import Counter, Histogram, start_http_server

class MonitoringConfig(BaseSettings):
    LOG_LEVEL: str = "INFO"
    METRICS_PORT: int = 9090
    
    # Prometheus metrics
    REQUEST_COUNT = Counter(
        'http_requests_total',
        'Total number of HTTP requests',
        ['method', 'endpoint', 'status']
    )
    
    REQUEST_LATENCY = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency in seconds',
        ['method', 'endpoint']
    )
    
    # Model metrics
    PREDICTION_COUNT = Counter(
        'model_predictions_total',
        'Total number of model predictions',
        ['model_version']
    )
    
    PREDICTION_LATENCY = Histogram(
        'model_prediction_duration_seconds',
        'Model prediction latency in seconds',
        ['model_version']
    )
    
    TRAINING_DURATION = Histogram(
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