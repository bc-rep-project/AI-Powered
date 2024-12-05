import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn
import asyncio
from src.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    required_vars = ["MONGODB_URL", "JWT_SECRET_KEY"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Log partial values for debugging (don't log sensitive info)
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            logger.info(f"Found environment variable {var}: {masked_value}")
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

async def startup_checks():
    """Perform all startup checks"""
    try:
        # Check environment variables first
        logger.info("Checking environment variables...")
        await check_environment()
        
        # Check database connection
        logger.info("Checking database connection...")
        db_connected = await check_database_connection()
        if not db_connected:
            raise ValueError("Failed to connect to database")
        
        logger.info("All startup checks passed successfully")
    except Exception as e:
        logger.error(f"Startup checks failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Load environment variables
        load_dotenv()
        logger.info("Starting application...")
        
        # Run startup checks
        asyncio.run(startup_checks())
        
        # Get port from environment variable
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting server on port {port}")
        
        # Start the application
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        sys.exit(1) 