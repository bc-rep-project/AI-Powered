"""
Render.com Free Tier Optimizer

This module contains utilities for automatically detecting and optimizing
application performance on Render.com's free tier environment.
"""

import os
import gc
import logging
import threading
import time
import shutil
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Constants
RENDER_ENV_VARS = ["RENDER", "RENDER_SERVICE_ID", "RENDER_INSTANCE_ID"]
TEMP_CLEANUP_INTERVAL = 60 * 60  # 1 hour
GC_INTERVAL = 15 * 60  # 15 minutes
LOG_CLEANUP_INTERVAL = 24 * 60 * 60  # 1 day
LOG_MAX_SIZE_MB = 20
DISK_USAGE_THRESHOLD = 80  # Percentage


def is_render_environment() -> bool:
    """Check if the application is running on Render.com"""
    return any(os.environ.get(var) is not None for var in RENDER_ENV_VARS)


def is_render_free_tier() -> bool:
    """
    Check if the application is running on Render.com's free tier.
    This uses heuristics based on Render's free tier limitations.
    """
    # Check explicit environment variable
    if os.environ.get("RENDER_FREE_TIER") == "1" or os.environ.get("FREE_TIER_MODE") == "true":
        return True
    
    # Check if we're on Render
    if not is_render_environment():
        return False
    
    # Additional heuristics for detecting free tier
    mem_limit = os.environ.get("RENDER_MEMORY_LIMIT")
    if mem_limit and int(mem_limit) <= 512:  # 512MB is free tier limit
        return True
    
    return False


def get_disk_usage() -> Dict[str, Any]:
    """Get disk usage information"""
    try:
        total, used, free = shutil.disk_usage("/")
        return {
            "total_mb": total / (1024 * 1024),
            "used_mb": used / (1024 * 1024),
            "free_mb": free / (1024 * 1024),
            "percent_used": (used / total) * 100
        }
    except Exception as e:
        logger.error(f"Error getting disk usage: {str(e)}")
        return {"error": str(e)}


def clean_temp_files():
    """Clean up temporary files to free disk space"""
    try:
        # Clean Python's tempdir
        temp_dir = tempfile.gettempdir()
        count = 0
        size_freed = 0
        
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                try:
                    # Skip files modified in the last hour
                    filepath = os.path.join(root, name)
                    if time.time() - os.path.getmtime(filepath) < 3600:
                        continue
                        
                    size = os.path.getsize(filepath)
                    os.unlink(filepath)
                    size_freed += size
                    count += 1
                except OSError:
                    pass
                    
            # Also try to remove empty directories
            for name in dirs:
                try:
                    dirpath = os.path.join(root, name)
                    os.rmdir(dirpath)  # Will only succeed if directory is empty
                except OSError:
                    pass
        
        logger.info(f"Cleaned {count} temporary files, freed {size_freed / (1024*1024):.2f} MB")
        return True
    except Exception as e:
        logger.error(f"Error cleaning temp files: {str(e)}")
        return False


def clean_old_logs():
    """Clean up old log files"""
    try:
        log_dir = os.path.join(os.getcwd(), "logs")
        if not os.path.exists(log_dir):
            return True
            
        count = 0
        size_freed = 0
        
        for root, _, files in os.walk(log_dir):
            for name in files:
                try:
                    filepath = os.path.join(root, name)
                    
                    # Check if older than 7 days
                    if time.time() - os.path.getmtime(filepath) > 7 * 24 * 60 * 60:
                        size = os.path.getsize(filepath)
                        os.unlink(filepath)
                        size_freed += size
                        count += 1
                    # Or check if file is too big
                    elif os.path.getsize(filepath) > LOG_MAX_SIZE_MB * 1024 * 1024:
                        # Truncate large log files
                        with open(filepath, "w") as f:
                            f.write(f"Log truncated at {datetime.now().isoformat()}\n")
                        size_freed += os.path.getsize(filepath)
                        count += 1
                except OSError:
                    pass
        
        logger.info(f"Cleaned {count} log files, freed {size_freed / (1024*1024):.2f} MB")
        return True
    except Exception as e:
        logger.error(f"Error cleaning logs: {str(e)}")
        return False


def clean_old_datasets():
    """Clean up old raw datasets to save disk space"""
    try:
        data_dir = os.path.join(os.getcwd(), "data", "raw")
        if not os.path.exists(data_dir):
            return True
            
        count = 0
        size_freed = 0
        
        for root, dirs, files in os.walk(data_dir):
            for name in files:
                try:
                    filepath = os.path.join(root, name)
                    
                    # Keep only files modified in the last 2 days
                    if time.time() - os.path.getmtime(filepath) > 2 * 24 * 60 * 60:
                        size = os.path.getsize(filepath)
                        os.unlink(filepath)
                        size_freed += size
                        count += 1
                except OSError:
                    pass
        
        logger.info(f"Cleaned {count} raw data files, freed {size_freed / (1024*1024):.2f} MB")
        return True
    except Exception as e:
        logger.error(f"Error cleaning datasets: {str(e)}")
        return False


def run_garbage_collection():
    """Run Python garbage collection"""
    try:
        count = gc.collect(generation=2)  # Full collection
        logger.info(f"Garbage collection completed: {count} objects collected")
        return count
    except Exception as e:
        logger.error(f"Error running garbage collection: {str(e)}")
        return 0


def run_scheduled_maintenance():
    """Run periodic maintenance tasks for free tier"""
    while True:
        try:
            # Check disk usage and clean if necessary
            disk_usage = get_disk_usage()
            if "percent_used" in disk_usage and disk_usage["percent_used"] > DISK_USAGE_THRESHOLD:
                logger.warning(f"High disk usage: {disk_usage['percent_used']:.1f}%. Running cleanup...")
                clean_temp_files()
                clean_old_logs()
                clean_old_datasets()
            
            # Run garbage collection
            run_garbage_collection()
            
            # Sleep before next check
            time.sleep(GC_INTERVAL)
            
            # Periodically clean temp files regardless of disk usage
            if int(time.time()) % TEMP_CLEANUP_INTERVAL < GC_INTERVAL:
                clean_temp_files()
            
            # Periodically clean logs
            if int(time.time()) % LOG_CLEANUP_INTERVAL < GC_INTERVAL:
                clean_old_logs()
        
        except Exception as e:
            logger.error(f"Error in maintenance thread: {str(e)}")
            time.sleep(60)  # Sleep a minute on error


def start_render_optimizer():
    """Start the Render optimizer if running on free tier"""
    if not is_render_free_tier():
        logger.info("Not running on Render free tier, optimizer not started")
        return False
    
    logger.info("Running on Render free tier, starting optimizer")
    
    # Start maintenance thread
    maintenance_thread = threading.Thread(
        target=run_scheduled_maintenance, 
        daemon=True,
        name="render-optimizer"
    )
    maintenance_thread.start()
    
    # Run initial cleanup
    run_garbage_collection()
    
    return True


def get_render_info() -> Dict[str, Any]:
    """Get information about the Render environment"""
    info = {
        "is_render": is_render_environment(),
        "is_free_tier": is_render_free_tier(),
        "time": datetime.now().isoformat(),
    }
    
    # Add disk usage
    disk_usage = get_disk_usage()
    if "error" not in disk_usage:
        info["disk_usage"] = disk_usage
    
    # Add memory info
    try:
        import psutil
        memory = psutil.virtual_memory()
        info["memory"] = {
            "total_mb": memory.total / (1024 * 1024),
            "available_mb": memory.available / (1024 * 1024),
            "percent_used": memory.percent
        }
    except ImportError:
        pass
    
    return info 