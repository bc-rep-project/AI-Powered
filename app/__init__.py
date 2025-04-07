"""
AI-Powered Content Recommendation API
"""

import sys
import logging
import subprocess

# Ensure the PyJWT package is installed
try:
    import jwt
except ImportError:
    try:
        import PyJWT
    except ImportError:
        logging.warning("PyJWT not found. Installing it now...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyJWT>=2.4.0"], check=True)
        
# Ensure other essential packages are installed
required_packages = [
    "pydantic>=1.8.0,<2.0.0",
    "fastapi>=0.88.0,<0.95.0",
    "uvicorn>=0.18.0"
]

for package in required_packages:
    try:
        # This will try to import the package to check if it's installed
        package_name = package.split(">=")[0].split("<")[0]
        __import__(package_name)
    except ImportError:
        logging.warning(f"{package_name} not found. Installing it now...")
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

__version__ = "1.0.0" 