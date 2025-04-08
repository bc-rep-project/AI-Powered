#!/usr/bin/env python3
import os
import json
import logging
import argparse
from datetime import datetime
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model class (should match train_model.py)
class RecommendationModel:
    def __init__(self, embedding_dim=32):
        self.embedding_dim = embedding_dim
        self.user_encoder = None
        self.content_encoder = None
        self.model = None
    
    @classmethod
    def load(cls, model_path):
        """Load the model and encoders"""
        # Load model info
        with open(os.path.join(model_path, 'model_info.json'), 'r') as f:
            model_info = json.load(f)
        
        # Create instance
        instance = cls(embedding_dim=model_info['embedding_dim'])
        
        # Load model
        instance.model = tf.keras.models.load_model(os.path.join(model_path, 'model'))
        
        # Load encoders
        user_classes = np.load(os.path.join(model_path, 'user_classes.npy'), allow_pickle=True)
        content_classes = np.load(os.path.join(model_path, 'content_classes.npy'), allow_pickle=True)
        
        instance.user_encoder = LabelEncoder()
        instance.user_encoder.classes_ = user_classes
        
        instance.content_encoder = LabelEncoder()
        instance.content_encoder.classes_ = content_classes
        
        logger.info(f"Model loaded from {model_path}")
        logger.info(f"Model info: {model_info}")
        
        return instance
    
    def get_recommendations(self, user_id, content_ids=None, top_k=10):
        """Get recommendations for a user"""
        if self.model is None:
            raise ValueError("Model has not been trained")
        
        try:
            # Encode user ID
            user_encoded = self.user_encoder.transform([user_id])[0]
        except:
            logger.warning(f"User {user_id} not in training data, using fallback")
            user_encoded = 0  # Use first user as fallback
        
        # If content_ids is not provided, use all content items
        if content_ids is None:
            content_encoded = np.arange(len(self.content_encoder.classes_))
        else:
            try:
                # Filter for content IDs that exist in the encoder
                valid_content_ids = []
                valid_encoded_ids = []
                
                for cid in content_ids:
                    try:
                        encoded = self.content_encoder.transform([cid])[0]
                        valid_content_ids.append(cid)
                        valid_encoded_ids.append(encoded)
                    except:
                        continue
                
                if not valid_content_ids:
                    logger.warning("No valid content IDs provided, using all content")
                    content_encoded = np.arange(len(self.content_encoder.classes_))
                    content_ids = self.content_encoder.classes_
                else:
                    content_encoded = np.array(valid_encoded_ids)
                    content_ids = valid_content_ids
            except:
                logger.warning("Error encoding content IDs, using all content")
                content_encoded = np.arange(len(self.content_encoder.classes_))
                content_ids = self.content_encoder.classes_
        
        # Create input arrays
        user_array = np.array([user_encoded] * len(content_encoded))
        
        # Get predictions
        predictions = self.model.predict([user_array, content_encoded], verbose=0).flatten()
        
        # Sort by prediction score and get top-k
        top_indices = np.argsort(predictions)[-top_k:][::-1]
        
        # Convert back to original IDs and create result list
        results = []
        for idx in top_indices:
            content_id = content_ids[idx] if isinstance(content_ids, list) else self.content_encoder.inverse_transform([content_encoded[idx]])[0]
            results.append((content_id, float(predictions[idx])))
        
        return results

# Pydantic models for API
class ContentItem(BaseModel):
    content_id: str
    title: str
    description: Optional[str] = None
    content_type: str = "movie"
    metadata: Optional[Dict] = None
    score: float

class RecommendationRequest(BaseModel):
    user_id: str
    limit: Optional[int] = 10
    content_filter: Optional[List[str]] = None

class RecommendationResponse(BaseModel):
    user_id: str
    recommendations: List[ContentItem]
    timestamp: str
    request_id: str

# Initialize FastAPI app
app = FastAPI(
    title="Recommendation API",
    description="API for serving content recommendations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
recommendation_model = None
content_items = {}

@app.on_event("startup")
async def startup_event():
    global recommendation_model, content_items
    
    # Create required directories
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Get model path from environment or use default
    model_path = os.getenv("MODEL_PATH", "models/latest")
    content_path = os.getenv("CONTENT_PATH", "data/processed/movielens-small")
    
    logger.info(f"Loading model from {model_path}")
    try:
        if os.path.exists(model_path):
            recommendation_model = RecommendationModel.load(model_path)
            logger.info(f"Model loaded successfully from {model_path}")
        else:
            logger.warning(f"Model path {model_path} does not exist, will serve fallback recommendations")
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        logger.warning("Will serve fallback recommendations")
    
    logger.info(f"Loading content from {content_path}")
    try:
        # Try to load content files
        content_file = os.path.join(content_path, "content_items.json")
        if os.path.exists(content_file):
            with open(content_file, "r") as f:
                content_items = json.load(f)
            logger.info(f"Loaded {len(content_items)} content items")
        else:
            # Check alternative paths
            alt_file = os.path.join(content_path, "movies.json")
            if os.path.exists(alt_file):
                with open(alt_file, "r") as f:
                    content_items = json.load(f)
                logger.info(f"Loaded {len(content_items)} content items from alternative file")
            else:
                logger.warning(f"Content file not found at {content_file} or {alt_file}")
                content_items = {}
    except Exception as e:
        logger.error(f"Error loading content: {str(e)}")
        content_items = {}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Recommendation API is running",
        "docs_url": "/docs",
        "status": "online"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": recommendation_model is not None,
        "content_items_loaded": len(content_items),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get personalized recommendations for a user"""
    if recommendation_model is None:
        raise HTTPException(status_code=503, detail="Recommendation model not loaded")
    
    try:
        # Get recommendations
        recs = recommendation_model.get_recommendations(
            user_id=request.user_id,
            top_k=request.limit
        )
        
        # Format response
        recommendation_items = []
        for content_id, score in recs:
            content_info = content_items.get(content_id, {
                "content_id": content_id,
                "title": f"Content {content_id}",
                "description": "No description available",
                "content_type": "unknown"
            })
            
            item = ContentItem(
                content_id=content_id,
                title=content_info.get("title", f"Content {content_id}"),
                description=content_info.get("description", "No description available"),
                content_type=content_info.get("content_type", "movie"),
                metadata=content_info.get("metadata", {}),
                score=score
            )
            recommendation_items.append(item)
        
        # Create response
        response = RecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendation_items,
            timestamp=datetime.now().isoformat(),
            request_id=f"req_{int(datetime.now().timestamp())}"
        )
        
        return response
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Start the recommendation API server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--model-path", type=str, default="models/latest", help="Path to the model directory")
    parser.add_argument("--content-path", type=str, default="data/processed/movielens-small", help="Path to the content data")
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["MODEL_PATH"] = args.model_path
    os.environ["CONTENT_PATH"] = args.content_path
    
    # Start server
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main() 