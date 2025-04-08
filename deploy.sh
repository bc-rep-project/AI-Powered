#!/bin/bash
set -e

echo "Starting deployment script for AI-Powered Content Recommendation API"

# Install core dependencies
echo "Installing core dependencies..."
pip install --upgrade pip

# Install authentication packages
echo "Installing authentication packages..."
pip install PyJWT>=2.4.0 python-jose>=3.3.0 passlib>=1.7.4 python-multipart>=0.0.5

# Install web framework and validation
echo "Installing web framework and validation packages..."
pip install fastapi>=0.100.0 uvicorn>=0.18.0 pydantic>=2.0.0 pydantic-settings>=2.0.0 email-validator>=2.0.0 

# Install database packages
echo "Installing database packages..."
pip install "sqlalchemy[asyncio]>=1.4.0" psycopg2-binary>=2.9.3 asyncpg>=0.27.0

# Install caching and messaging
echo "Installing caching and messaging packages..."
pip install redis>=4.2.0

# Install utility packages
echo "Installing utility packages..."
pip install requests>=2.27.0 python-dotenv>=0.20.0

# Check if auth.py imports are correct
AUTH_FILE="app/routes/auth.py"
if [ -f "$AUTH_FILE" ]; then
    echo "Checking JWT imports in $AUTH_FILE"
    if ! grep -q "try.*import jwt.*except.*import PyJWT" "$AUTH_FILE"; then
        echo "Fixing jwt import in $AUTH_FILE"
        # Create a backup
        cp "$AUTH_FILE" "${AUTH_FILE}.bak"
        # Replace the import with a proper try-except block
        sed -i '0,/import jwt/s/import jwt/try:\n    import jwt\nexcept ImportError:\n    try:\n        import PyJWT as jwt\n        logging.info("Using PyJWT instead of jwt")\n    except ImportError:\n        logging.error("Could not import jwt or PyJWT. Installing PyJWT...")\n        import subprocess\n        subprocess.run([sys.executable, "-m", "pip", "install", "PyJWT>=2.4.0"], check=True)\n        import PyJWT as jwt/' "$AUTH_FILE"
    fi
    
    # Fix AsyncSession import if needed
    if grep -q "from sqlalchemy.orm import .*AsyncSession" "$AUTH_FILE" || grep -q "from sqlalchemy.ext.asyncio import AsyncSession" "$AUTH_FILE"; then
        echo "Checking AsyncSession usage in $AUTH_FILE"
        if ! grep -q "try.*from sqlalchemy.ext.asyncio import AsyncSession.*except" "$AUTH_FILE"; then
            echo "Adding fallback for AsyncSession in $AUTH_FILE"
            cp "$AUTH_FILE" "${AUTH_FILE}.bak.async"
            # Add proper try-except for AsyncSession
            sed -i '/from sqlalchemy.orm import Session/a\
# Import AsyncSession with proper fallback\
try:\
    from sqlalchemy.ext.asyncio import AsyncSession\
except ImportError:\
    # For older SQLAlchemy versions or when async is not available\
    from sqlalchemy.orm import Session as AsyncSession' "$AUTH_FILE"
        fi
    fi
fi

# Setup directories
mkdir -p data/raw data/processed models

# Install app-specific requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
fi

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