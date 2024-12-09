import tensorflow as tf
import numpy as np
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta
import os
import json
from app.core.training_config import training_config
from app.models.neural_recommender import NeuralRecommender
from app.db.database import mongodb, redis_client
import logging

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.model: Optional[NeuralRecommender] = None
        self.current_version: int = 0
        self._setup_directories()

    def _setup_directories(self):
        """Create necessary directories for model checkpoints and saves"""
        try:
            os.makedirs(training_config.MODEL_CHECKPOINT_DIR, exist_ok=True)
            os.makedirs(training_config.MODEL_SAVE_PATH, exist_ok=True)
            os.makedirs(training_config.TENSORBOARD_LOG_DIR, exist_ok=True)
            logger.info("Successfully created model directories")
        except Exception as e:
            logger.error(f"Failed to create model directories: {str(e)}")
            raise

    async def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare training data from user interactions."""
        # Get all interactions
        interactions = await mongodb.user_interactions.find().to_list(None)
        
        # Convert to numpy arrays
        user_ids = []
        item_ids = []
        labels = []
        
        for interaction in interactions:
            user_ids.append(interaction["user_id"])
            item_ids.append(interaction["content_id"])
            # Convert interaction type to label (e.g., view=0.5, like=1.0)
            label = 1.0 if interaction["interaction_type"] in ["like", "purchase"] else 0.5
            labels.append(label)
        
        return (
            np.array(user_ids),
            np.array(item_ids),
            np.array(labels)
        )

    def _create_model(self, num_users: int, num_items: int) -> NeuralRecommender:
        """Create a new model instance."""
        return NeuralRecommender(
            num_users=num_users,
            num_items=num_items,
            embedding_dim=training_config.EMBEDDING_DIM
        )

    def _create_dataset(
        self,
        user_ids: np.ndarray,
        item_ids: np.ndarray,
        labels: np.ndarray
    ) -> tf.data.Dataset:
        """Create TensorFlow dataset for training."""
        dataset = tf.data.Dataset.from_tensor_slices((
            {
                "user_input": user_ids,
                "item_input": item_ids
            },
            labels
        ))
        
        return dataset.shuffle(10000).batch(training_config.BATCH_SIZE)

    async def train_model(self) -> Dict[str, float]:
        """Train the recommendation model."""
        # Check if we should train
        if not self._should_train():
            return {}
        
        # Prepare data
        user_ids, item_ids, labels = await self.prepare_training_data()
        
        # Create datasets
        dataset = self._create_dataset(user_ids, item_ids, labels)
        
        # Split into train/val/test
        total_size = len(user_ids)
        val_size = int(total_size * training_config.VALIDATION_SPLIT)
        test_size = int(total_size * training_config.TEST_SPLIT)
        train_size = total_size - val_size - test_size
        
        train_dataset = dataset.take(train_size)
        val_dataset = dataset.skip(train_size).take(val_size)
        test_dataset = dataset.skip(train_size + val_size)
        
        # Create or get model
        if self.model is None:
            num_users = len(set(user_ids))
            num_items = len(set(item_ids))
            self.model = self._create_model(num_users, num_items)
        
        # Compile model
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(training_config.LEARNING_RATE),
            loss=tf.keras.losses.BinaryCrossentropy(),
            metrics=[
                tf.keras.metrics.BinaryAccuracy(),
                tf.keras.metrics.AUC()
            ]
        )
        
        # Train model
        history = self.model.fit(
            train_dataset,
            epochs=training_config.EPOCHS,
            validation_data=val_dataset,
            callbacks=[
                tf.keras.callbacks.ModelCheckpoint(
                    filepath=os.path.join(
                        training_config.MODEL_CHECKPOINT_DIR,
                        "model_{epoch:02d}_{val_loss:.2f}.h5"
                    ),
                    save_best_only=True,
                    monitor="val_loss"
                ),
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    patience=3,
                    restore_best_weights=True
                )
            ]
        )
        
        # Evaluate model
        test_results = self.model.evaluate(test_dataset)
        metrics = {
            "test_loss": float(test_results[0]),
            "test_accuracy": float(test_results[1]),
            "test_auc": float(test_results[2])
        }
        
        # Save best model
        self.model.save_weights(training_config.MODEL_SAVE_PATH)
        
        # Update training metadata
        self.current_version += 1
        
        # Clear recommendation cache
        await self._clear_cache()
        
        return metrics

    def _should_train(self) -> bool:
        """Determine if model should be retrained."""
        if self.current_version == 0:
            return True
            
        time_since_last_training = datetime.utcnow() - self.last_training_time
        hours_since_last_training = time_since_last_training.total_seconds() / 3600
        
        return (
            hours_since_last_training >= training_config.RETRAIN_INTERVAL_HOURS or
            self.new_interactions_count >= training_config.MIN_NEW_INTERACTIONS
        )

    async def _clear_cache(self):
        """Clear recommendation cache after model update."""
        # Get all keys matching recommendations:*
        pattern = "recommendations:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)

    def load_model(self):
        """Load the best model weights."""
        if os.path.exists(training_config.MODEL_SAVE_PATH + ".index"):
            self.model.load_weights(training_config.MODEL_SAVE_PATH)

    def increment_interactions_count(self):
        """Increment the count of new interactions."""
        self.new_interactions_count += 1 