import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any

def calculate_user_content_matrix(interactions: List[Dict[str, Any]]) -> np.ndarray:
    """
    Create a user-content interaction matrix from interaction data
    """
    # Extract unique users and content ids
    user_ids = list(set(interaction["user_id"] for interaction in interactions))
    content_ids = list(set(interaction["content_id"] for interaction in interactions))
    
    # Create mapping dictionaries
    user_to_idx = {user_id: idx for idx, user_id in enumerate(user_ids)}
    content_to_idx = {content_id: idx for idx, content_id in enumerate(content_ids)}
    
    # Initialize interaction matrix
    matrix = np.zeros((len(user_ids), len(content_ids)))
    
    # Fill matrix with interaction data
    for interaction in interactions:
        user_idx = user_to_idx[interaction["user_id"]]
        content_idx = content_to_idx[interaction["content_id"]]
        # Weight different interaction types
        weight = {
            "view": 1,
            "click": 2,
            "like": 3,
            "share": 4,
            "purchase": 5
        }.get(interaction["interaction_type"], 1)
        matrix[user_idx, content_idx] += weight
    
    return matrix, user_to_idx, content_to_idx

def get_similar_items(item_features: np.ndarray, item_id: int, n: int = 5) -> List[tuple]:
    """
    Find similar items based on feature similarity
    """
    similarities = cosine_similarity([item_features[item_id]], item_features)[0]
    similar_indices = np.argsort(similarities)[::-1][1:n+1]
    return [(idx, similarities[idx]) for idx in similar_indices]

def get_user_recommendations(user_item_matrix: np.ndarray, user_id: int, n: int = 5) -> List[tuple]:
    """
    Get recommendations for a user using collaborative filtering
    """
    user_similarities = cosine_similarity([user_item_matrix[user_id]], user_item_matrix)[0]
    similar_users = np.argsort(user_similarities)[::-1][1:6]  # Get top 5 similar users
    
    # Get items that similar users interacted with
    recommendations = []
    user_items = set(np.nonzero(user_item_matrix[user_id])[0])
    
    for similar_user in similar_users:
        items = set(np.nonzero(user_item_matrix[similar_user])[0])
        new_items = items - user_items
        for item in new_items:
            score = user_similarities[similar_user] * user_item_matrix[similar_user, item]
            recommendations.append((item, score))
    
    # Sort and return top N recommendations
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return recommendations[:n] 