import tensorflow as tf
from tensorflow.keras import layers, Model
from typing import List, Tuple
import numpy as np
from app.core.config import settings

class NeuralRecommender(Model):
    def __init__(
        self,
        num_users: int,
        num_items: int,
        embedding_dim: int = settings.EMBEDDING_DIM
    ):
        super(NeuralRecommender, self).__init__()
        
        # User embedding layer
        self.user_embedding = layers.Embedding(
            num_users,
            embedding_dim,
            embeddings_initializer="he_normal",
            embeddings_regularizer=tf.keras.regularizers.l2(1e-6)
        )
        
        # Item embedding layer
        self.item_embedding = layers.Embedding(
            num_items,
            embedding_dim,
            embeddings_initializer="he_normal",
            embeddings_regularizer=tf.keras.regularizers.l2(1e-6)
        )
        
        # Neural network layers
        self.dense_layers = [
            layers.Dense(256, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(64, activation="relu"),
            layers.Dense(1, activation="sigmoid")
        ]

    def call(self, inputs: Tuple[tf.Tensor, tf.Tensor]) -> tf.Tensor:
        user_input, item_input = inputs
        
        # Get embeddings
        user_embedded = self.user_embedding(user_input)
        item_embedded = self.item_embedding(item_input)
        
        # Concatenate embeddings
        x = tf.concat([user_embedded, item_embedded], axis=1)
        
        # Pass through dense layers
        for layer in self.dense_layers:
            x = layer(x)
            
        return x

    def get_user_embedding(self, user_id: int) -> np.ndarray:
        """Get the embedding vector for a user."""
        return self.user_embedding(tf.constant([user_id]))[0].numpy()

    def get_item_embedding(self, item_id: int) -> np.ndarray:
        """Get the embedding vector for an item."""
        return self.item_embedding(tf.constant([item_id]))[0].numpy()

    def predict_score(self, user_id: int, item_id: int) -> float:
        """Predict the interaction score between a user and an item."""
        return self.call((
            tf.constant([user_id]),
            tf.constant([item_id])
        ))[0][0].numpy()

    def get_recommendations(
        self,
        user_id: int,
        item_ids: List[int],
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """Get top-k recommendations for a user from a list of items."""
        scores = []
        for item_id in item_ids:
            score = self.predict_score(user_id, item_id)
            scores.append((item_id, score))
        
        # Sort by score and return top-k
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k] 