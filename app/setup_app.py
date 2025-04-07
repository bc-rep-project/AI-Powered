#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(command):
    """Run a command and log output"""
    logger.info(f"Running command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        logger.info(f"Command output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def setup_app():
    """Setup the application for production"""
    logger.info("Starting application setup...")
    
    # Create required directories
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Set environment variables
    dataset = "movielens-small"
    raw_dir = "data/raw"
    processed_dir = "data/processed"
    model_dir = "models"
    
    # Check if we already have processed data
    if not os.path.exists(f"{processed_dir}/{dataset}/content_items.json"):
        logger.info("Processed data not found. Downloading and processing dataset...")
        
        # Install requirements for data processing
        run_command("pip install requests pandas tqdm numpy zipfile36")
        
        # Download and process dataset
        script_path = str(Path(__file__).parent.parent / "scripts" / "data_processor.py")
        if not run_command(f"python {script_path} --dataset {dataset} --raw-dir {raw_dir} --processed-dir {processed_dir}"):
            logger.error("Failed to download and process dataset")
            return False
    else:
        logger.info("Processed data already exists. Skipping download and processing.")
    
    # Check if we already have a trained model
    if not os.path.exists(f"{model_dir}/latest"):
        logger.info("Trained model not found. Training a new model...")
        
        # Install requirements for model training
        run_command("pip install tensorflow scikit-learn matplotlib")
        
        # Train model
        script_path = str(Path(__file__).parent.parent / "scripts" / "train_model.py")
        if not run_command(f"python {script_path} --data-dir {processed_dir}/{dataset} --model-dir {model_dir} --epochs 10 --batch-size 64"):
            logger.error("Failed to train model")
            return False
        
        # Create symbolic link to latest model (find the most recent model directory)
        try:
            model_dirs = [d for d in os.listdir(model_dir) if d.startswith("recommender_")]
            if model_dirs:
                latest_model = sorted(model_dirs)[-1]
                os.symlink(latest_model, f"{model_dir}/latest")
                logger.info(f"Created symbolic link to {latest_model}")
        except Exception as e:
            logger.error(f"Failed to create symbolic link: {e}")
            # Continue anyway as this is not critical
    else:
        logger.info("Trained model already exists. Skipping model training.")
    
    logger.info("App setup completed successfully!")
    return True

if __name__ == "__main__":
    if setup_app():
        logger.info("Setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("Setup failed!")
        sys.exit(1) 