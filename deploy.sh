#!/bin/bash
set -e

echo "Starting deployment script for AI-Powered Content Recommendation API"

# Install core dependencies
echo "Installing core dependencies..."
pip install --upgrade pip
pip install PyJWT>=2.4.0 requests>=2.27.0 fastapi>=0.100.0 uvicorn>=0.18.0 pydantic>=2.0.0 pydantic-settings>=2.0.0 sqlalchemy>=1.4.0 psycopg2-binary>=2.9.3

# Check if auth.py imports are correct
AUTH_FILE="app/routes/auth.py"
if [ -f "$AUTH_FILE" ]; then
    if grep -q "import jwt" "$AUTH_FILE"; then
        echo "Fixing jwt import in $AUTH_FILE"
        # Create a backup
        cp "$AUTH_FILE" "${AUTH_FILE}.bak"
        # Replace the import
        sed -i 's/import jwt/try:\n    import jwt\nexcept ImportError:\n    import PyJWT as jwt/' "$AUTH_FILE"
    fi
fi

# Setup directories
mkdir -p data/raw data/processed models

# Run app setup script if it exists
if [ -f "app/setup_app.py" ]; then
    echo "Running app setup script..."
    python app/setup_app.py
fi

# Set environment variables
export MODEL_PATH="models/latest"
export CONTENT_PATH="data/processed/movielens-small"

# Start the application
echo "Starting the application..."
cd app
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" 