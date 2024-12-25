from typing import List, Dict
import random
from datetime import datetime

class RecommendationModel:
    """Simple recommendation model for development."""
    
    def __init__(self):
        self.version = "0.1.0"
        self.algorithm_type = "collaborative_filtering"
        self._interactions = []
        self._content_embeddings = {}
        self._user_embeddings = {}

    def train(self, interactions: List[Dict], epochs: int = 5, batch_size: int = 32):
        """Train the recommendation model."""
        self._interactions.extend(interactions)
        # In a real implementation, this would train the model
        # For now, just store the interactions

    def get_recommendations(self, user_id: str, n: int = 10) -> List[Dict]:
        """Get recommendations for a user."""
        # For development, return dummy recommendations
        return [
            {
                "content_id": f"content{i}",
                "score": round(0.9 - (i * 0.1), 2),
                "rank": i + 1,
                "title": f"Sample Content {i}",
                "description": f"This is a sample content item {i}",
                "type": "article" if i % 2 == 0 else "video",
                "metadata": {
                    "tags": [f"tag{j}" for j in range(3)],
                    "category": f"category{i % 5}"
                }
            }
            for i in range(n)
        ]

    def update_user_preferences(self, user_id: str, preferences: Dict):
        """Update user preferences."""
        if user_id not in self._user_embeddings:
            self._user_embeddings[user_id] = {}
        self._user_embeddings[user_id].update(preferences)

    def add_interaction(self, user_id: str, content_id: str, interaction_type: str):
        """Add a new user-content interaction."""
        self._interactions.append({
            "user_id": user_id,
            "content_id": content_id,
            "interaction_type": interaction_type,
            "timestamp": datetime.utcnow().isoformat()
        }) 