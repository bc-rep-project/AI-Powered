"""
AI-Powered Content Recommendation API
"""

import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check for JWT
try:
    import jwt
except ImportError:
    try:
        import PyJWT as jwt
        logger.info("Using PyJWT instead of jwt")
    except ImportError:
        logger.warning("JWT module not found. Attempting to install PyJWT...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT>=2.4.0"])
            import PyJWT as jwt
            logger.info("Successfully installed PyJWT")
        except Exception as e:
            logger.error(f"Failed to install PyJWT: {str(e)}")

# Check for pydantic-settings
try:
    from pydantic_settings import BaseSettings
except ImportError:
    logger.warning("pydantic-settings not found. Attempting to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pydantic-settings>=2.0.0"])
        from pydantic_settings import BaseSettings
        logger.info("Successfully installed pydantic-settings")
    except Exception as e:
        logger.error(f"Failed to install pydantic-settings: {str(e)}")

# Check other required packages
required_packages = [
    "pydantic>=2.0.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.22.0",
    "sqlalchemy>=1.4.0",
    "email-validator>=2.0.0",
    "passlib>=1.7.4",
    "python-jose>=3.3.0",
    "python-multipart>=0.0.5"
]

for package in required_packages:
    try:
        package_name = package.split('>=')[0]
        __import__(package_name)
        logger.info(f"Package {package_name} already installed")
    except ImportError:
        logger.warning(f"{package_name} not found. Attempting to install {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logger.info(f"Successfully installed {package}")
        except Exception as e:
            logger.error(f"Failed to install {package_name}: {str(e)}")

# Try to import and set up SQLAlchemy async
try:
    import sqlalchemy.ext.asyncio
    logger.info("SQLAlchemy async extensions available")
except ImportError:
    logger.warning("SQLAlchemy async extensions not found. Attempting to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlalchemy[asyncio]>=1.4.0"])
        logger.info("Successfully installed SQLAlchemy with async support")
    except Exception as e:
        logger.error(f"Failed to install SQLAlchemy async extensions: {str(e)}")
        logger.warning("Using synchronous SQLAlchemy instead")

# Try to import and set up Redis async
try:
    from redis import asyncio as aioredis
    logger.info("Redis async client available")
except ImportError:
    logger.warning("Redis async client not found. Attempting to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "redis>=4.2.0"])
        logger.info("Successfully installed async Redis client")
    except Exception as e:
        logger.error(f"Failed to install async Redis client: {str(e)}")
        logger.warning("Redis functionality will be limited")

# Try to import database drivers
try:
    import psycopg2
except ImportError:
    logger.warning("psycopg2 not found. Attempting to install psycopg2-binary...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary>=2.9.3"])
        logger.info("Successfully installed psycopg2-binary")
    except Exception as e:
        logger.error(f"Failed to install psycopg2-binary: {str(e)}")

# App version
__version__ = "1.0.0" 