"""
Resource management utilities for optimizing performance on Render.com free tier.
This module helps control memory usage, CPU utilization, and provides throttling mechanisms.
"""
import logging
import time
import gc
import asyncio
import os
from datetime import datetime
from functools import wraps
from typing import Callable, Any, Optional, Dict

logger = logging.getLogger(__name__)

# Try to import psutil for resource monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available. Resource monitoring will be limited.")

from ..core.config import settings

class ResourceMonitor:
    """Monitor and manage system resources to prevent Render.com hibernation."""
    
    def __init__(self):
        self.last_gc_time = time.time()
        self.memory_warning_threshold = settings.MAX_MEMORY_PERCENT
        self.cpu_warning_threshold = settings.MAX_CPU_PERCENT
        self.gc_threshold = settings.GC_THRESHOLD
        self.free_tier_mode = settings.FREE_TIER_MODE
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}
        
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                "memory_used_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "cpu_percent": cpu_percent,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return {"error": str(e)}
    
    def check_resources(self) -> bool:
        """
        Check if system resources are within acceptable limits.
        Returns True if resources are OK, False if they're constrained.
        """
        if not self.free_tier_mode or not PSUTIL_AVAILABLE:
            return True
            
        try:
            usage = self.get_resource_usage()
            
            # Log resource usage periodically
            if "memory_used_percent" in usage:
                memory_percent = usage["memory_used_percent"]
                cpu_percent = usage["cpu_percent"]
                
                if memory_percent > self.memory_warning_threshold:
                    logger.warning(f"High memory usage: {memory_percent:.1f}% (threshold: {self.memory_warning_threshold}%)")
                    self.reduce_memory_pressure()
                    return False
                    
                if cpu_percent > self.cpu_warning_threshold:
                    logger.warning(f"High CPU usage: {cpu_percent:.1f}% (threshold: {self.cpu_warning_threshold}%)")
                    return False
                    
                # Run garbage collection if memory usage exceeds GC threshold
                if memory_percent > self.gc_threshold and time.time() - self.last_gc_time > 60:
                    logger.info(f"Running garbage collection. Memory usage: {memory_percent:.1f}%")
                    self.force_garbage_collection()
            
            return True
        except Exception as e:
            logger.error(f"Error checking resources: {str(e)}")
            return True  # Default to allowing operation if checking fails
    
    def reduce_memory_pressure(self):
        """Reduce memory pressure by forcing garbage collection and other optimizations."""
        self.force_garbage_collection()
        
        # Release any cached objects here
        # ...
    
    def force_garbage_collection(self):
        """Force Python garbage collection."""
        collected = gc.collect()
        self.last_gc_time = time.time()
        logger.info(f"Garbage collection completed. {collected} objects collected.")
    
    async def wait_for_resources(self, interval: float = 1.0, max_wait: float = 30.0) -> bool:
        """
        Wait until resources are available or max_wait is reached.
        Returns True if resources became available, False if max_wait was reached.
        """
        if not self.free_tier_mode:
            return True
            
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.check_resources():
                return True
            await asyncio.sleep(interval)
        
        return False

# Create a singleton instance
resource_monitor = ResourceMonitor()

def check_resource_usage():
    """Check resource usage and log if thresholds are exceeded."""
    return resource_monitor.check_resources()

def resource_intensive_task(func):
    """
    Decorator for resource-intensive tasks.
    Will check resource usage before executing and potentially delay execution.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if we're in free tier mode
        if not settings.FREE_TIER_MODE:
            return await func(*args, **kwargs)
        
        # Wait for resources to be available
        resources_available = await resource_monitor.wait_for_resources()
        if not resources_available:
            logger.warning(f"Executing {func.__name__} despite resource constraints")
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            # Clean up after intensive task
            if settings.ENABLE_MEMORY_OPTIMIZATION:
                resource_monitor.force_garbage_collection()
    
    return wrapper

def process_in_chunks(chunk_size: Optional[int] = None, sleep_time: Optional[float] = None):
    """
    Decorator to process an iterable in chunks with optional sleep between chunks.
    This helps prevent CPU spikes on Render.com's free tier.
    
    Parameters:
    - chunk_size: Size of each chunk (default from settings)
    - sleep_time: Time to sleep between chunks in seconds (default from settings)
    """
    if chunk_size is None:
        chunk_size = settings.DATA_PROCESSING_CHUNK_SIZE
    
    if sleep_time is None:
        sleep_time = settings.DATA_PROCESSING_SLEEP_SEC
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(items, *args, **kwargs):
            result = []
            for i in range(0, len(items), chunk_size):
                # Process a chunk
                chunk = items[i:i + chunk_size]
                chunk_result = await func(chunk, *args, **kwargs)
                if chunk_result:
                    if isinstance(result, list):
                        result.extend(chunk_result)
                    else:
                        result = chunk_result
                
                # Sleep to prevent CPU spike
                if i + chunk_size < len(items) and sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
                # Check resources
                if not resource_monitor.check_resources():
                    # If resources are constrained, wait longer
                    await asyncio.sleep(sleep_time * 3)
            
            return result
        
        @wraps(func)
        def sync_wrapper(items, *args, **kwargs):
            result = []
            for i in range(0, len(items), chunk_size):
                # Process a chunk
                chunk = items[i:i + chunk_size]
                chunk_result = func(chunk, *args, **kwargs)
                if chunk_result:
                    if isinstance(result, list):
                        result.extend(chunk_result)
                    else:
                        result = chunk_result
                
                # Sleep to prevent CPU spike
                if i + chunk_size < len(items) and sleep_time > 0:
                    time.sleep(sleep_time)
                    
                # Check resources
                if not resource_monitor.check_resources():
                    # If resources are constrained, wait longer
                    time.sleep(sleep_time * 3)
            
            return result
        
        # Determine which wrapper to return based on if the wrapped function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

def is_within_time_window() -> bool:
    """
    Check if current time is within the specified window for intensive operations.
    Returns True if current time is within the window or if no window is configured.
    """
    # If auto-retraining is disabled, time window doesn't matter
    if not settings.ENABLE_AUTO_RETRAINING:
        return False
        
    # Get current hour (0-23)
    current_hour = datetime.now().hour
    
    # Check if current hour is within the window
    start_hour = settings.RETRAINING_TIME_WINDOW_START
    end_hour = settings.RETRAINING_TIME_WINDOW_END
    
    # Handle window that crosses midnight
    if start_hour <= end_hour:
        return start_hour <= current_hour < end_hour
    else:
        return current_hour >= start_hour or current_hour < end_hour 