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
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.model = None
        self.current_version = 0
        self.last_training_time = datetime.utcnow()
        self.new_interactions_count = 0
        
        self.checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(
                training_config.MODEL_CHECKPOINT_DIR,
                "model_{epoch:02d}_{loss:.2f}.keras"
            ),
            save_best_only=True,
            monitor='loss',
            mode='min',
            verbose=1
        )
        
        self.early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='loss',
            patience=training_config.EARLY_STOPPING_PATIENCE,
            restore_best_weights=True
        )
        
        # Create model directories
        os.makedirs(training_config.MODEL_CHECKPOINT_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(training_config.MODEL_SAVE_PATH), exist_ok=True)
        logger.info("Successfully created model directories")

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
        model = NeuralRecommender(
            num_users=num_users,
            num_items=num_items,
            embedding_dim=training_config.EMBEDDING_DIM
        )
        
        # Build model graph
        model = model.build_graph()
        
        # Compile model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(training_config.LEARNING_RATE),
            loss=tf.keras.losses.BinaryCrossentropy(),
            metrics=[
                tf.keras.metrics.BinaryAccuracy(),
                tf.keras.metrics.AUC()
            ]
        )
        
        return model

    def _create_dataset(
        self,
        user_ids: np.ndarray,
        item_ids: np.ndarray,
        labels: np.ndarray,
        is_training: bool = True
    ) -> tf.data.Dataset:
        """Create TensorFlow dataset for training or validation."""
        if len(user_ids) == 0:
            raise ValueError("Empty dataset provided")
        
        dataset = tf.data.Dataset.from_tensor_slices((
            {
                "user_input": user_ids,
                "item_input": item_ids
            },
            labels
        ))
        
        # Shuffle only training data
        if is_training:
            dataset = dataset.shuffle(10000)
        
        # Always batch
        dataset = dataset.batch(training_config.BATCH_SIZE)
        
        # Repeat only training data
        if is_training:
            dataset = dataset.repeat()
        
        return dataset

    async def train_model(self) -> Dict[str, float]:
        """Train the recommendation model."""
        try:
            # Check if we should train
            if not self._should_train():
                return {}
            
            # Prepare data
            user_ids, item_ids, labels = await self.prepare_training_data()
            if len(user_ids) == 0:
                logger.warning("No training data available")
                return {}
            
            # Split data
            indices = np.random.permutation(len(user_ids))
            train_idx, val_idx = train_test_split(
                indices, 
                test_size=training_config.VALIDATION_SPLIT
            )
            
            # Create datasets
            train_dataset = self._create_dataset(
                user_ids[train_idx],
                item_ids[train_idx],
                labels[train_idx],
                is_training=True
            )
            
            val_dataset = self._create_dataset(
                user_ids[val_idx],
                item_ids[val_idx],
                labels[val_idx],
                is_training=False
            )
            
            # Create or get model
            if self.model is None:
                num_users = len(np.unique(user_ids))
                num_items = len(np.unique(item_ids))
                self.model = self._create_model(num_users, num_items)
            
            # Calculate steps
            steps_per_epoch = len(train_idx) // training_config.BATCH_SIZE
            validation_steps = len(val_idx) // training_config.BATCH_SIZE
            
            # Update checkpoint callback
            self.checkpoint_callback.filepath = os.path.join(
                training_config.MODEL_CHECKPOINT_DIR,
                f"model_{{epoch:02d}}_{{binary_accuracy:.2f}}.keras"
            )
            self.checkpoint_callback.monitor = "binary_accuracy"
            self.checkpoint_callback.mode = "max"
            
            # Train model
            history = await self.model.fit(
                train_dataset,
                epochs=training_config.EPOCHS,
                steps_per_epoch=steps_per_epoch,
                validation_data=val_dataset,
                validation_steps=validation_steps,
                callbacks=[
                    self.checkpoint_callback,
                    self.early_stopping
                ]
            )
            
            # Save final model
            self.model.save(training_config.MODEL_SAVE_PATH)
            
            # Update metadata
            self.current_version += 1
            self.last_training_time = datetime.utcnow()
            self.new_interactions_count = 0
            
            # Clear cache
            await self._clear_cache()
            
            return {
                "train_loss": float(history.history["loss"][-1]),
                "train_accuracy": float(history.history["binary_accuracy"][-1]),
                "val_loss": float(history.history["val_loss"][-1]),
                "val_accuracy": float(history.history["val_binary_accuracy"][-1])
            }
            
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            raise

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