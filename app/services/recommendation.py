import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..models.content import Content
from ..models.interaction import Interaction
import tensorflow as tf
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db
        self.model = None
        self.content_embeddings = {}
        self.user_embeddings = {}

    async def train_collaborative_filtering(self):
        """Train the collaborative filtering model using user-content interactions"""
        try:
            # Get all interactions
            interactions_df = pd.read_sql(
                self.db.query(Interaction).statement,
                self.db.bind
            )

            # Create user-item interaction matrix
            interaction_matrix = pd.pivot_table(
                interactions_df,
                values='value',
                index='user_id',
                columns='content_id',
                fill_value=0
            )

            # Initialize neural network model
            self.model = tf.keras.Sequential([
                tf.keras.layers.Dense(64, activation='relu'),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.Dense(32, activation='relu'),
                tf.keras.layers.Dense(interaction_matrix.shape[1])
            ])

            self.model.compile(
                optimizer='adam',
                loss='mean_squared_error'
            )

            # Train the model
            self.model.fit(
                interaction_matrix.values,
                interaction_matrix.values,
                epochs=10,
                batch_size=32,
                validation_split=0.2
            )

            logger.info("Collaborative filtering model trained successfully")
        except Exception as e:
            logger.error(f"Error training collaborative filtering model: {str(e)}")
            raise

    async def get_content_based_recommendations(
        self,
        user_id: int,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get content-based recommendations based on user's interaction history"""
        try:
            # Get user's recent interactions
            user_interactions = self.db.query(Interaction).filter(
                Interaction.user_id == user_id
            ).order_by(Interaction.created_at.desc()).limit(50).all()

            if not user_interactions:
                return []

            # Get content details for user's interactions
            interacted_content_ids = [i.content_id for i in user_interactions]
            interacted_content = self.db.query(Content).filter(
                Content.id.in_(interacted_content_ids)
            ).all()

            # Calculate content similarity
            all_content = self.db.query(Content)
            if content_type:
                all_content = all_content.filter(Content.content_type == content_type)
            all_content = all_content.all()

            # Use content embeddings for similarity calculation
            content_vectors = np.array([
                self._get_content_embedding(c) for c in all_content
            ])
            
            user_profile = np.mean([
                self._get_content_embedding(c) for c in interacted_content
            ], axis=0)

            # Calculate similarity scores
            similarities = cosine_similarity([user_profile], content_vectors)[0]

            # Get top recommendations
            content_scores = list(zip(all_content, similarities))
            content_scores.sort(key=lambda x: x[1], reverse=True)

            # Filter out already interacted content
            recommendations = [
                {
                    "content_id": content.id,
                    "title": content.title,
                    "type": content.content_type,
                    "score": float(score)
                }
                for content, score in content_scores
                if content.id not in interacted_content_ids
            ][:limit]

            return recommendations

        except Exception as e:
            logger.error(f"Error getting content-based recommendations: {str(e)}")
            raise

    async def get_collaborative_recommendations(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Get collaborative filtering recommendations"""
        try:
            if not self.model:
                await self.train_collaborative_filtering()

            # Get user's interaction vector
            user_interactions = self.db.query(Interaction).filter(
                Interaction.user_id == user_id
            ).all()

            if not user_interactions:
                return []

            # Create user vector
            user_vector = np.zeros(self.model.output_shape[-1])
            for interaction in user_interactions:
                user_vector[interaction.content_id] = interaction.value

            # Get predictions
            predictions = self.model.predict(np.array([user_vector]))[0]

            # Get content details
            content_scores = list(enumerate(predictions))
            content_scores.sort(key=lambda x: x[1], reverse=True)

            # Filter out already interacted content
            interacted_content_ids = {i.content_id for i in user_interactions}
            recommendations = []

            for content_id, score in content_scores:
                if content_id not in interacted_content_ids:
                    content = self.db.query(Content).filter(
                        Content.id == content_id
                    ).first()
                    if content:
                        recommendations.append({
                            "content_id": content.id,
                            "title": content.title,
                            "type": content.content_type,
                            "score": float(score)
                        })
                        if len(recommendations) >= limit:
                            break

            return recommendations

        except Exception as e:
            logger.error(f"Error getting collaborative recommendations: {str(e)}")
            raise

    def _get_content_embedding(self, content: Content) -> np.ndarray:
        """Get or compute content embedding"""
        if content.id not in self.content_embeddings:
            # Here you would implement your embedding logic
            # This could use pre-trained models like BERT for text
            # or ResNet for images, depending on your content type
            # For now, we'll use a simple placeholder
            embedding = np.random.rand(128)  # 128-dimensional embedding
            self.content_embeddings[content.id] = embedding
        return self.content_embeddings[content.id] 