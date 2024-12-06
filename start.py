import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn
import asyncio
from src.database import Database
import signal

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def check_database_connection():
    """Check if database connection is working"""
    try:
        await Database.connect_db()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

async def check_environment():
    """Check required environment variables"""
    required_vars = [
        "MONGODB_URL",
        "JWT_SECRET_KEY",
        "ENVIRONMENT",
        "PORT"
    ]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Log partial values for debugging (don't log sensitive info)
            if var in ["MONGODB_URL", "JWT_SECRET_KEY"]:
                masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            else:
                masked_value = value
            logger.info(f"Found environment variable {var}: {masked_value}")
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

async def startup_checks():
    """Perform all startup checks"""
    try:
        logger.info("Starting application initialization...")
        
        # Check environment variables first
        logger.info("Checking environment variables...")
        await check_environment()
        
        # Check database connection
        logger.info("Checking database connection...")
        if not await check_database_connection():
            raise Exception("Failed to establish database connection")
        
        logger.info("All startup checks passed successfully")
        return True
    except Exception as e:
        logger.error(f"Startup checks failed: {str(e)}")
        return False

def handle_shutdown(signum, frame):
    """Handle graceful shutdown"""
    logger.info("Received shutdown signal, cleaning up...")
    asyncio.create_task(Database.close_db())
    sys.exit(0)

if __name__ == "__main__":
    # Register shutdown handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Run startup checks
    if not asyncio.run(startup_checks()):
        logger.error("Startup checks failed, exiting...")
        sys.exit(1)
    
    # Start the application
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        workers=int(os.getenv("WEB_CONCURRENCY", 4)),
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    ) 