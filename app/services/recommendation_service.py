import numpy as np
from typing import List, Dict, Optional
from app.models.recommendation import UserProfile, ContentItem, Recommendation, UserInteraction
from app.models.neural_recommender import NeuralRecommender
from app.db.database import user_profiles, content_items, user_interactions, redis_client
from app.core.config import settings
from app.training.task_manager import task_manager
import json
import tensorflow as tf

class RecommendationService:
    def __init__(self):
        self.user_id_map: Dict[str, int] = {}
        self.content_id_map: Dict[str, int] = {}

    async def generate_recommendations(
        self,
        user_profile: UserProfile,
        n_recommendations: int = 10
    ) -> List[Recommendation]:
        """Generate personalized recommendations for a user."""
        # Try to get cached recommendations
        cache_key = f"recommendations:{user_profile.user_id}"
        cached = redis_client.get(cache_key)
        
        if cached:
            return [Recommendation(**json.loads(r)) for r in json.loads(cached)]
        
        try:
            # Get user's interaction history
            user_interactions_list = await user_interactions.find(
                {"user_id": user_profile.user_id}
            ).to_list(None)
            
            # Get all content items
            all_content = await content_items.find().to_list(None)
            
            # Convert IDs for model
            user_id_int = self._get_user_id_int(user_profile.user_id)
            content_id_ints = [
                self._get_content_id_int(c["content_id"])
                for c in all_content
            ]
            
            # Get recommendations from model
            recommendations = []
            model = task_manager.get_trainer().model
            
            if model:
                top_items = model.get_recommendations(
                    user_id_int,
                    content_id_ints,
                    top_k=n_recommendations
                )
                
                for content_id_int, score in top_items:
                    content_id = self._get_content_id_str(content_id_int)
                    content = await content_items.find_one({"content_id": content_id})
                    
                    if content:
                        recommendation = Recommendation(
                            user_id=user_profile.user_id,
                            content_items=[ContentItem(**content)],
                            score=float(score),
                            explanation="Based on your interaction history and similar users' preferences"
                        )
                        recommendations.append(recommendation)
            
            # Cache recommendations
            if recommendations:
                redis_client.setex(
                    cache_key,
                    300,  # Cache for 5 minutes
                    json.dumps([r.dict() for r in recommendations])
                )
            
            return recommendations
            
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return []

    async def update_user_profile(self, user_profile: UserProfile):
        """Update user profile and retrain/update recommendations."""
        try:
            # Update user profile in database
            await user_profiles.update_one(
                {"user_id": user_profile.user_id},
                {"$set": user_profile.dict()},
                upsert=True
            )
            
            # Invalidate cache
            redis_client.delete(f"recommendations:{user_profile.user_id}")
            
        except Exception as e:
            print(f"Error updating user profile: {e}")

    async def add_content_item(self, content_item: ContentItem):
        """Add new content item to the recommendation system."""
        try:
            # Store content item in database
            await content_items.update_one(
                {"content_id": content_item.content_id},
                {"$set": content_item.dict()},
                upsert=True
            )
            
            # Update content ID mapping
            content_id_int = len(self.content_id_map)
            self.content_id_map[content_item.content_id] = content_id_int
            
        except Exception as e:
            print(f"Error adding content item: {e}")

    async def record_interaction(self, interaction: UserInteraction):
        """Record a user interaction and update recommendations."""
        try:
            # Store interaction in database
            await user_interactions.insert_one(interaction.dict())
            
            # Invalidate cache
            redis_client.delete(f"recommendations:{interaction.user_id}")
            
            # Increment interaction count for training
            task_manager.get_trainer().increment_interactions_count()
            
        except Exception as e:
            print(f"Error recording interaction: {e}")

    def _get_user_id_int(self, user_id: str) -> int:
        """Convert string user ID to integer for model."""
        if user_id not in self.user_id_map:
            self.user_id_map[user_id] = len(self.user_id_map)
        return self.user_id_map[user_id]

    def _get_content_id_int(self, content_id: str) -> int:
        """Convert string content ID to integer for model."""
        if content_id not in self.content_id_map:
            self.content_id_map[content_id] = len(self.content_id_map)
        return self.content_id_map[content_id]

    def _get_content_id_str(self, content_id_int: int) -> str:
        """Convert integer content ID back to string."""
        for k, v in self.content_id_map.items():
            if v == content_id_int:
                return k
        return str(content_id_int)