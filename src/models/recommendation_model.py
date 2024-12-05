import numpy as np
from typing import List, Dict, Any, Tuple
import tensorflow as tf
from sklearn.preprocessing import StandardScaler
from ..utils.recommendation_utils import calculate_user_content_matrix, get_similar_items, get_user_recommendations

class RecommendationModel:
    def __init__(self, embedding_dim: int = 32):
        self.embedding_dim = embedding_dim
        self.user_embedding = None
        self.content_embedding = None
        self.model = None
        self.user_to_idx = {}
        self.content_to_idx = {}
        self.scaler = StandardScaler()
        
    def build_model(self, n_users: int, n_items: int):
        """Build the neural collaborative filtering model"""
        # User input
        user_input = tf.keras.layers.Input(shape=(1,))
        user_embedding = tf.keras.layers.Embedding(n_users, self.embedding_dim)(user_input)
        user_vec = tf.keras.layers.Flatten()(user_embedding)
        
        # Item input
        item_input = tf.keras.layers.Input(shape=(1,))
        item_embedding = tf.keras.layers.Embedding(n_items, self.embedding_dim)(item_input)
        item_vec = tf.keras.layers.Flatten()(item_embedding)
        
        # Merge layers
        concat = tf.keras.layers.Concatenate()([user_vec, item_vec])
        dense1 = tf.keras.layers.Dense(64, activation='relu')(concat)
        dense2 = tf.keras.layers.Dense(32, activation='relu')(dense1)
        dense3 = tf.keras.layers.Dense(16, activation='relu')(dense2)
        output = tf.keras.layers.Dense(1, activation='sigmoid')(dense3)
        
        self.model = tf.keras.Model(inputs=[user_input, item_input], outputs=output)
        self.model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
    
    def prepare_data(self, interactions: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare interaction data for training"""
        matrix, self.user_to_idx, self.content_to_idx = calculate_user_content_matrix(interactions)
        
        # Create training data
        user_indices = []
        item_indices = []
        labels = []
        
        for user_id in range(matrix.shape[0]):
            for item_id in range(matrix.shape[1]):
                user_indices.append(user_id)
                item_indices.append(item_id)
                labels.append(1 if matrix[user_id, item_id] > 0 else 0)
        
        return np.array(user_indices), np.array(item_indices), np.array(labels)
    
    def train(self, interactions: List[Dict[str, Any]], epochs: int = 10, batch_size: int = 64):
        """Train the recommendation model"""
        user_indices, item_indices, labels = self.prepare_data(interactions)
        
        if self.model is None:
            self.build_model(len(self.user_to_idx), len(self.content_to_idx))
        
        self.model.fit(
            [user_indices, item_indices],
            labels,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2
        )
    
    def get_recommendations(self, user_id: str, n: int = 5) -> List[Dict[str, Any]]:
        """Get personalized recommendations for a user"""
        if user_id not in self.user_to_idx:
            return []
        
        user_idx = self.user_to_idx[user_id]
        predictions = []
        
        # Predict scores for all items
        for content_idx in range(len(self.content_to_idx)):
            score = self.model.predict(
                [np.array([user_idx]), np.array([content_idx])],
                verbose=0
            )[0][0]
            predictions.append((content_idx, score))
        
        # Sort and get top N recommendations
        predictions.sort(key=lambda x: x[1], reverse=True)
        top_n = predictions[:n]
        
        # Convert indices back to content IDs
        idx_to_content = {idx: content_id for content_id, idx in self.content_to_idx.items()}
        recommendations = [
            {
                "content_id": idx_to_content[idx],
                "score": float(score),
                "rank": rank + 1
            }
            for rank, (idx, score) in enumerate(top_n)
        ]
        
        return recommendations
    
    def get_similar_content(self, content_id: str, n: int = 5) -> List[Dict[str, Any]]:
        """Get similar content items"""
        if content_id not in self.content_to_idx:
            return []
        
        content_idx = self.content_to_idx[content_id]
        content_embedding = self.model.get_layer('embedding_2').get_weights()[0]
        similar_items = get_similar_items(content_embedding, content_idx, n)
        
        # Convert indices back to content IDs
        idx_to_content = {idx: content_id for content_id, idx in self.content_to_idx.items()}
        similar_content = [
            {
                "content_id": idx_to_content[idx],
                "similarity_score": float(score),
                "rank": rank + 1
            }
            for rank, (idx, score) in enumerate(similar_items)
        ]
        
        return similar_content 