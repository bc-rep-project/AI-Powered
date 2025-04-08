#!/bin/bash
set -e

echo "Installing essential dependencies for recommendation system..."

# Upgrade pip first
pip install --upgrade pip

# Install core ML dependencies with specified versions
echo "Installing TensorFlow and scikit-learn..."
pip install "tensorflow>=2.8.0,<2.11.0" "scikit-learn>=1.0.0" 

echo "Installing pandas and numpy..."
pip install "pandas>=1.3.0" "numpy>=1.20.0"

echo "Installing matplotlib and visualization tools..."
pip install "matplotlib>=3.5.0" "seaborn>=0.11.0" "tqdm>=4.60.0"

# Install web framework components
echo "Installing FastAPI and related packages..."
pip install "fastapi>=0.100.0" "uvicorn>=0.18.0" "pydantic>=2.0.0" "pydantic-settings>=2.0.0"

# Install utilities
echo "Installing utility packages..."
pip install "requests>=2.27.0" "python-dotenv>=0.20.0" "psutil>=5.9.0"

# Install authentication packages
echo "Installing authentication packages..."
pip install "PyJWT>=2.4.0" "python-jose>=3.3.0" "passlib>=1.7.4" "python-multipart>=0.0.5"

# Install database packages
echo "Installing database packages..."
pip install "sqlalchemy>=1.4.0" "psycopg2-binary>=2.9.3" "redis>=4.0.0"

# Install data processing tools
echo "Installing data processing tools..."
pip install "zipfile36>=0.1.0"

echo "Installation complete!" 