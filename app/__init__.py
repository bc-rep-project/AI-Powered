"""
AI-Powered Content Recommendation API
"""

import sys
import logging
import subprocess

# Check for JWT
try:
    import jwt
except ImportError:
    try:
        import PyJWT as jwt
    except ImportError:
        logging.warning("JWT module not found. Attempting to install PyJWT...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT>=2.4.0"])

# Check other required packages
required_packages = [
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.22.0"
]

for package in required_packages:
    try:
        package_name = package.split('>=')[0]
        __import__(package_name)
    except ImportError:
        logging.warning(f"{package_name} not found. Attempting to install {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# App version
__version__ = "1.0.0" 