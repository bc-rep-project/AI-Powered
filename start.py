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

async def startup_checks():
    """Perform all startup checks"""
    # Check database connection
    db_connected = await check_database_connection()
    if not db_connected:
        logger.error("Failed to connect to database. Exiting...")
        sys.exit(1)
    
    # Check required environment variables
    required_vars = ["JWT_SECRET_KEY", "MONGODB_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Load environment variables
        load_dotenv()
        
        # Run startup checks
        asyncio.run(startup_checks())
        
        # Get port from environment variable
        port = int(os.environ.get("PORT", 8080))
        
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