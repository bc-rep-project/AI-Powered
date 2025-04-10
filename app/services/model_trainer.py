"""
Lightweight movie recommendation model trainer optimized for Render.com free tier.
Uses simple matrix factorization approach to avoid high resource usage.
"""

import os
import logging
import json
import time
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import pickle
from sklearn.preprocessing import LabelEncoder
import sqlite3
import threading
from ..db.mongodb import get_mongodb
from ..db.redis import get_redis
from ..core.config import settings
from ..services.dataset_manager import PROCESSED_DIR, get_movie_by_id

logger = logging.getLogger(__name__)

# Constants for model training
MODELS_DIR = "models"
RECOMMENDER_DIR = os.path.join(MODELS_DIR, "recommender")
EMBEDDINGS_FILE = "embeddings.npz"
MODEL_METADATA_FILE = "metadata.json"
LAST_TRAINED_KEY = "model:last_trained"
MAX_INTERACTIONS = 50000  # Limit to avoid memory issues
BATCH_SIZE = 1000
EMBEDDING_SIZE = 50  # Size of embedding vectors
MODEL_TRAINING_EXPIRY_DAYS = 1  # Retrain after this many days

# Ensure directories exist
os.makedirs(RECOMMENDER_DIR, exist_ok=True)

class ModelTrainingStatus:
    """Status tracker for model training operations"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.start_time = datetime.now()
        self.progress = 0.0
        self.status = "initializing"
        self.message = "Starting model training"
        self.error = None
    
    async def update(self, status: str, progress: float, message: str, error: Optional[str] = None):
        """Update status and save to Redis"""
        self.status = status
        self.progress = progress
        self.message = message
        self.error = error
        
        # Save status to Redis for tracking
        try:
            redis = await get_redis()
            if redis:
                await redis.hset(
                    f"model_job:{self.job_id}",
                    mapping={
                        "status": status,
                        "progress": str(progress),
                        "message": message,
                        "error": error or "",
                        "updated_at": datetime.now().isoformat()
                    }
                )
                # Set expiration to avoid cluttering Redis
                await redis.expire(f"model_job:{self.job_id}", 60 * 60 * 24)  # 24 hours
        except Exception as e:
            logger.error(f"Error updating model status in Redis: {str(e)}")

async def check_if_recently_trained() -> bool:
    """Check if model was recently trained (within MODEL_TRAINING_EXPIRY_DAYS)"""
    try:
        redis = await get_redis()
        if redis:
            last_trained = await redis.get(LAST_TRAINED_KEY)
            if last_trained:
                last_date = datetime.fromisoformat(last_trained)
                days_ago = (datetime.now() - last_date).days
                return days_ago < MODEL_TRAINING_EXPIRY_DAYS
        
        # If Redis not available, check local file
        metadata_file = os.path.join(RECOMMENDER_DIR, MODEL_METADATA_FILE)
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                if 'trained_at' in metadata:
                    last_date = datetime.fromisoformat(metadata['trained_at'])
                    days_ago = (datetime.now() - last_date).days
                    return days_ago < MODEL_TRAINING_EXPIRY_DAYS
                    
        return False
    except Exception as e:
        logger.error(f"Error checking last trained time: {str(e)}")
        return False

async def mark_trained_complete():
    """Mark the model as recently trained"""
    timestamp = datetime.now().isoformat()
    try:
        redis = await get_redis()
        if redis:
            await redis.set(LAST_TRAINED_KEY, timestamp)
            # Reset new interactions counter
            await redis.set("new_interactions_count", "0")
            
        # Always update metadata file as backup
        metadata_file = os.path.join(RECOMMENDER_DIR, MODEL_METADATA_FILE)
        
        metadata = {
            'trained_at': timestamp,
            'model_version': str(uuid.uuid4()),
            'embedding_size': EMBEDDING_SIZE
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
            
    except Exception as e:
        logger.error(f"Error marking training complete: {str(e)}")

async def get_interactions_for_training(max_interactions: int = MAX_INTERACTIONS) -> List[Dict[str, Any]]:
    """
    Get interactions for model training, with limit to avoid memory issues
    """
    try:
        # Try MongoDB first
        mongodb = await get_mongodb()
        interactions = []
        
        if mongodb:
            # Get most recent interactions
            cursor = mongodb["interactions"].find().sort("timestamp", -1).limit(max_interactions)
            async for interaction in cursor:
                if "_id" in interaction:
                    del interaction["_id"]
                interactions.append(interaction)
            
            logger.info(f"Loaded {len(interactions)} interactions from MongoDB")
            return interactions
        
        # Fallback to local file - first try user interactions
        interactions_path = os.path.join(PROCESSED_DIR, "movielens-small", "user_interactions.json")
        if os.path.exists(interactions_path):
            with open(interactions_path, 'r') as f:
                try:
                    user_interactions = json.load(f)
                    interactions.extend(user_interactions)
                except Exception as e:
                    logger.error(f"Error loading user interactions: {str(e)}")
        
        # Then add pre-loaded MovieLens interactions if needed
        if len(interactions) < max_interactions:
            ml_path = os.path.join(PROCESSED_DIR, "movielens-small", "interactions.json")
            if os.path.exists(ml_path):
                with open(ml_path, 'r') as f:
                    try:
                        ml_interactions = json.load(f)
                        # Take only what we need to reach max_interactions
                        remaining = max_interactions - len(interactions)
                        interactions.extend(ml_interactions[:remaining])
                    except Exception as e:
                        logger.error(f"Error loading MovieLens interactions: {str(e)}")
        
        logger.info(f"Loaded {len(interactions)} interactions from local files")
        return interactions
    except Exception as e:
        logger.error(f"Error getting interactions for training: {str(e)}")
        return []

class SimpleMatrixFactorizationModel:
    """
    A simple matrix factorization model optimized for memory usage.
    Uses user_id and content_id to predict ratings.
    """
    def __init__(self, embedding_size: int = EMBEDDING_SIZE):
        self.embedding_size = embedding_size
        self.user_encoder = LabelEncoder()
        self.content_encoder = LabelEncoder()
        self.user_embeddings = None
        self.content_embeddings = None
        self.user_biases = None
        self.content_biases = None
        self.global_bias = 0.0
        self.model_version = str(uuid.uuid4())
        self.sqlite_conn = None
        self.trained = False
    
    def _prepare_data(self, interactions: List[Dict[str, Any]]):
        """Prepare data for training by encoding IDs and extracting values"""
        user_ids = [i["user_id"] for i in interactions]
        content_ids = [i["content_id"] for i in interactions]
        values = np.array([float(i["value"]) for i in interactions])
        
        # Encode IDs to integers
        user_indices = self.user_encoder.fit_transform(user_ids)
        content_indices = self.content_encoder.fit_transform(content_ids)
        
        return user_indices, content_indices, values
    
    def train(self, interactions: List[Dict[str, Any]], 
              learning_rate: float = 0.005, 
              regularization: float = 0.02, 
              epochs: int = 20,
              status: Optional[ModelTrainingStatus] = None) -> Dict[str, Any]:
        """
        Train the model using batch gradient descent
        """
        logger.info(f"Starting model training with {len(interactions)} interactions")
        
        # Prepare data
        user_indices, content_indices, values = self._prepare_data(interactions)
        
        # Initialize model parameters
        n_users = len(self.user_encoder.classes_)
        n_contents = len(self.content_encoder.classes_)
        
        # Initialize parameters with small random values
        np.random.seed(42)  # For reproducibility
        self.user_embeddings = np.random.normal(0, 0.1, (n_users, self.embedding_size))
        self.content_embeddings = np.random.normal(0, 0.1, (n_contents, self.embedding_size))
        self.user_biases = np.zeros(n_users)
        self.content_biases = np.zeros(n_contents)
        self.global_bias = np.mean(values)
        
        # Training loop with batches
        n_samples = len(values)
        indices = np.arange(n_samples)
        history = {"loss": []}
        
        for epoch in range(epochs):
            # Shuffle data for each epoch
            np.random.shuffle(indices)
            epoch_loss = 0.0
            
            # Process in batches to save memory
            for i in range(0, n_samples, BATCH_SIZE):
                batch_indices = indices[i:i+BATCH_SIZE]
                batch_user_indices = user_indices[batch_indices]
                batch_content_indices = content_indices[batch_indices]
                batch_values = values[batch_indices]
                
                # Forward pass for batch
                predictions = self._predict_batch(batch_user_indices, batch_content_indices)
                batch_error = batch_values - predictions
                batch_loss = np.mean(np.square(batch_error))
                epoch_loss += batch_loss * len(batch_indices) / n_samples
                
                # Gradient descent updates
                for j, (u, c, err) in enumerate(zip(batch_user_indices, batch_content_indices, batch_error)):
                    # Update user and content embeddings
                    user_grad = -err * self.content_embeddings[c] + regularization * self.user_embeddings[u]
                    content_grad = -err * self.user_embeddings[u] + regularization * self.content_embeddings[c]
                    
                    self.user_embeddings[u] -= learning_rate * user_grad
                    self.content_embeddings[c] -= learning_rate * content_grad
                    
                    # Update biases
                    self.user_biases[u] -= learning_rate * (-err + regularization * self.user_biases[u])
                    self.content_biases[c] -= learning_rate * (-err + regularization * self.content_biases[c])
            
            history["loss"].append(epoch_loss)
            logger.info(f"Epoch {epoch+1}/{epochs}, Loss: {epoch_loss:.4f}")
            
            # Update status if provided
            if status:
                message = f"Epoch {epoch+1}/{epochs}, Loss: {epoch_loss:.4f}"
                progress = 0.2 + (0.7 * (epoch + 1) / epochs)
                await status.update("training", progress, message)
        
        # Mark as trained
        self.trained = True
        
        return history
    
    def _predict_batch(self, user_indices, content_indices):
        """
        Compute predictions for a batch of user-content pairs
        """
        predictions = np.zeros(len(user_indices))
        
        for i, (u, c) in enumerate(zip(user_indices, content_indices)):
            # Dot product of user and content embeddings + biases
            predictions[i] = (
                np.dot(self.user_embeddings[u], self.content_embeddings[c]) + 
                self.user_biases[u] + 
                self.content_biases[c] + 
                self.global_bias
            )
        
        return predictions
    
    def predict(self, user_id: str, content_id: str) -> float:
        """
        Predict rating for a user-content pair
        """
        if not self.trained:
            return self.global_bias
        
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
            content_idx = self.content_encoder.transform([content_id])[0]
            
            prediction = (
                np.dot(self.user_embeddings[user_idx], self.content_embeddings[content_idx]) + 
                self.user_biases[user_idx] + 
                self.content_biases[content_idx] + 
                self.global_bias
            )
            
            # Clip to rating range (typically 1-5)
            return max(1.0, min(5.0, prediction))
        except:
            # User or content not in training data
            return self.global_bias
    
    def get_recommendations(self, user_id: str, n: int = 10) -> List[Tuple[str, float]]:
        """
        Get top-N recommendations for a user
        """
        if not self.trained:
            return []
            
        try:
            user_idx = self.user_encoder.transform([user_id])[0]
            
            # Calculate scores for all content items
            scores = []
            for content_idx, content_id in enumerate(self.content_encoder.classes_):
                score = (
                    np.dot(self.user_embeddings[user_idx], self.content_embeddings[content_idx]) + 
                    self.user_biases[user_idx] + 
                    self.content_biases[content_idx] + 
                    self.global_bias
                )
                scores.append((content_id, score))
            
            # Sort by score and return top N
            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[:n]
        except:
            # User not in training data
            return []
    
    def save(self, model_dir: str = RECOMMENDER_DIR):
        """
        Save model to files, separating components to reduce memory usage
        """
        os.makedirs(model_dir, exist_ok=True)
        
        # Save encoders
        with open(os.path.join(model_dir, 'encoders.pkl'), 'wb') as f:
            pickle.dump({
                'user_encoder': self.user_encoder,
                'content_encoder': self.content_encoder
            }, f)
        
        # Save embeddings using sparse format to save memory
        np.savez(
            os.path.join(model_dir, EMBEDDINGS_FILE),
            user_embeddings=self.user_embeddings,
            content_embeddings=self.content_embeddings,
            user_biases=self.user_biases,
            content_biases=self.content_biases
        )
        
        # Save other parameters
        with open(os.path.join(model_dir, 'params.json'), 'w') as f:
            json.dump({
                'global_bias': float(self.global_bias),
                'embedding_size': self.embedding_size,
                'model_version': self.model_version,
                'n_users': len(self.user_encoder.classes_),
                'n_items': len(self.content_encoder.classes_),
                'trained_at': datetime.now().isoformat()
            }, f)
            
        # Create a symlink to the latest model
        latest_dir = os.path.join(MODELS_DIR, "latest")
        try:
            if os.path.exists(latest_dir) and os.path.islink(latest_dir):
                os.unlink(latest_dir)
            os.symlink(model_dir, latest_dir)
        except Exception as e:
            logger.error(f"Error creating symlink to latest model: {str(e)}")
        
        logger.info(f"Model saved to {model_dir}")
    
    @classmethod
    def load(cls, model_dir: str = RECOMMENDER_DIR) -> Optional['SimpleMatrixFactorizationModel']:
        """
        Load model from files
        """
        try:
            # Load encoders
            with open(os.path.join(model_dir, 'encoders.pkl'), 'rb') as f:
                encoders = pickle.load(f)
                
            # Load embeddings
            npz_file = os.path.join(model_dir, EMBEDDINGS_FILE)
            if not os.path.exists(npz_file):
                logger.error(f"Embeddings file not found: {npz_file}")
                return None
                
            embeddings = np.load(npz_file)
            
            # Load other parameters
            with open(os.path.join(model_dir, 'params.json'), 'r') as f:
                params = json.load(f)
            
            # Create model instance
            model = cls(embedding_size=params['embedding_size'])
            model.user_encoder = encoders['user_encoder']
            model.content_encoder = encoders['content_encoder']
            model.user_embeddings = embeddings['user_embeddings']
            model.content_embeddings = embeddings['content_embeddings'] 
            model.user_biases = embeddings['user_biases']
            model.content_biases = embeddings['content_biases']
            model.global_bias = params['global_bias']
            model.model_version = params['model_version']
            model.trained = True
            
            logger.info(f"Model loaded from {model_dir}")
            return model
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return None

async def run_training_pipeline(job_id: str, force: bool = False) -> bool:
    """
    Run the full model training pipeline
    """
    status = ModelTrainingStatus(job_id)
    
    try:
        # Check if already trained recently
        if not force and await check_if_recently_trained():
            logger.info("Model was recently trained, skipping training")
            await status.update("skipped", 1.0, "Model was recently trained, skipping training")
            return True
        
        # Ensure directory exists
        os.makedirs(RECOMMENDER_DIR, exist_ok=True)
        
        # Step 1: Load interactions
        await status.update("loading", 0.1, "Loading interaction data")
        interactions = await get_interactions_for_training()
        
        if len(interactions) == 0:
            error_msg = "No interactions found for training"
            logger.error(error_msg)
            await status.update("failed", 0.1, error_msg, error_msg)
            return False
        
        logger.info(f"Loaded {len(interactions)} interactions for training")
        
        # Step 2: Train model
        await status.update("training", 0.2, "Starting model training")
        model = SimpleMatrixFactorizationModel()
        
        # Run training in a separate thread to avoid blocking event loop
        history = await model.train(interactions, status=status)
        
        # Step 3: Save model
        await status.update("saving", 0.9, "Saving model")
        model.save()
        
        # Step 4: Mark training as complete
        await mark_trained_complete()
        
        await status.update("complete", 1.0, "Model training complete")
        return True
        
    except Exception as e:
        error_msg = f"Error in training pipeline: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await status.update("failed", 0.0, "Training pipeline failed", error_msg)
        return False

async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status of a model training job"""
    try:
        redis = await get_redis()
        if redis:
            status = await redis.hgetall(f"model_job:{job_id}")
            if status:
                # Convert progress to float
                if "progress" in status:
                    status["progress"] = float(status["progress"])
                return status
        return {"status": "not_found", "message": f"Job {job_id} not found"}
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return {"status": "error", "message": f"Error getting job status: {str(e)}"}

async def get_model_recommendations(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recommendations for a user based on trained model
    """
    try:
        # Try to load the model
        model = SimpleMatrixFactorizationModel.load()
        
        if not model or not model.trained:
            logger.warning("Model not available, returning empty recommendations")
            return []
        
        # Get raw recommendations
        raw_recommendations = model.get_recommendations(user_id, limit * 2)  # Get extra in case we can't find all movies
        
        # Enrich with movie details
        recommendations = []
        for content_id, score in raw_recommendations:
            movie = await get_movie_by_id(content_id)
            if movie:
                movie["score"] = float(score)
                recommendations.append(movie)
            
            if len(recommendations) >= limit:
                break
        
        return recommendations[:limit]
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return [] 