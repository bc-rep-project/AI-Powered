#!/bin/bash

# Configuration
DATASET="movielens-small"
RAW_DATA_DIR="data/raw"
PROCESSED_DATA_DIR="data/processed"
MODEL_DIR="models"
EVALUATION_DIR="evaluation"
API_PORT=8000

# Create directories
mkdir -p $RAW_DATA_DIR $PROCESSED_DATA_DIR $MODEL_DIR $EVALUATION_DIR

# Step 1: Install required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Step 2: Download and process dataset
echo "Downloading and processing dataset: $DATASET"
python scripts/data_processor.py --dataset $DATASET --raw-dir $RAW_DATA_DIR --processed-dir $PROCESSED_DATA_DIR

# Step 3: Train the recommendation model
echo "Training recommendation model..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODEL_PATH="$MODEL_DIR/recommender_$TIMESTAMP"
python scripts/train_model.py --data-dir "$PROCESSED_DATA_DIR/$DATASET" --model-dir $MODEL_DIR --epochs 20 --batch-size 64

# Create symbolic link to the latest model
ln -sf $MODEL_PATH "$MODEL_DIR/latest"

# Step 4: Evaluate the model
echo "Evaluating model..."
python scripts/evaluate_model.py --model-path $MODEL_PATH --data-path "$PROCESSED_DATA_DIR/$DATASET/sample" --output-dir "$EVALUATION_DIR/$TIMESTAMP"

# Step 5: Start the recommendation API server
echo "Starting API server on port $API_PORT..."
echo "Press Ctrl+C to stop the server"
python scripts/model_server.py --model-path $MODEL_PATH --content-path "$PROCESSED_DATA_DIR/$DATASET" --port $API_PORT

# Note: The script will stop here while the API server is running
# To stop the server, press Ctrl+C 