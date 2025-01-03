from typing import List, Optional, Dict, Any
import numpy as np
from datetime import datetime
from ...data.processing.features import process_content_features

class RecommenderModel:
    def __init__(self):
        self.model = None
        self.content_features = None
        self.user_embeddings = None
        
    def train(self, user_data: Dict[str, Any], content_data: Dict[str, Any]):
        """Train the recommendation model."""
        # Process features
        user_features = self._process_user_features(user_data)
        self.content_features = process_content_features(content_data)
        
        # Train model (implement specific algorithm in subclasses)
        self._train_model(user_features, self.content_features)
        
    def _train_model(self, user_features, content_features):
        """Implement specific training logic in subclasses."""
        raise NotImplementedError
        
    def get_recommendations(
        self,
        user_id: str,
        user_data: Dict[str, Any],
        limit: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get personalized recommendations for a user."""
        # Get user embedding
        user_embedding = self._get_user_embedding(user_id, user_data)
        
        # Get content scores
        scores = self._get_content_scores(user_embedding)
        
        # Filter by category if specified
        if category:
            category_mask = [c['category'] == category for c in self.content_features]
            scores = scores * category_mask
            
        # Get top recommendations
        top_indices = np.argsort(scores)[-limit:][::-1]
        
        recommendations = []
        for idx in top_indices:
            content = self.content_features[idx]
            recommendations.append({
                'id': content['id'],
                'title': content['title'],
                'description': content['description'],
                'category': content['category'],
                'score': float(scores[idx]),
                'tags': content['tags'],
                'created_at': datetime.utcnow(),
                'relevance_explanation': self._get_explanation(user_data, content)
            })
            
        return recommendations
        
    def get_diverse_recommendations(
        self,
        user_id: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get diverse recommendations for exploration."""
        # Get base recommendations
        base_recs = self.get_recommendations(user_id, {}, limit=limit*2)
        
        # Apply diversity optimization
        diverse_recs = self._diversify_recommendations(base_recs)
        
        # Apply filters
        filtered_recs = self._apply_filters(diverse_recs, category, tags)
        
        return filtered_recs[:limit]
        
    def _get_user_embedding(self, user_id: str, user_data: Dict[str, Any]):
        """Get or compute user embedding."""
        if user_id in self.user_embeddings:
            return self.user_embeddings[user_id]
        return self._compute_user_embedding(user_data)
        
    def _compute_user_embedding(self, user_data: Dict[str, Any]):
        """Compute user embedding from user data."""
        # Implement in subclasses
        raise NotImplementedError
        
    def _get_content_scores(self, user_embedding):
        """Compute content scores based on user embedding."""
        # Implement in subclasses
        raise NotImplementedError
        
    def _get_explanation(self, user_data: Dict[str, Any], content: Dict[str, Any]) -> str:
        """Generate explanation for why this content was recommended."""
        # Implement simple explanation logic
        # Could be enhanced with more sophisticated approaches
        if not user_data:
            return "Recommended based on popularity and relevance"
            
        explanations = []
        
        # Check category match
        if user_data.get('preferred_categories'):
            if content['category'] in user_data['preferred_categories']:
                explanations.append(f"Matches your interest in {content['category']}")
                
        # Check tag overlap
        if user_data.get('preferred_tags'):
            matching_tags = set(content['tags']) & set(user_data['preferred_tags'])
            if matching_tags:
                explanations.append(f"Contains topics you're interested in: {', '.join(matching_tags)}")
                
        # Check similar content interactions
        if user_data.get('interactions'):
            similar_content = [i for i in user_data['interactions'] 
                             if i['category'] == content['category']]
            if similar_content:
                explanations.append(f"Similar to content you've enjoyed in {content['category']}")
                
        if not explanations:
            return "Recommended based on your overall preferences"
            
        return " • ".join(explanations)
        
    def _diversify_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply diversity optimization to recommendations."""
        diverse_recs = []
        seen_categories = set()
        seen_tags = set()
        
        for rec in recommendations:
            # Skip if too similar to already selected items
            if (rec['category'] in seen_categories and 
                any(tag in seen_tags for tag in rec['tags'])):
                continue
                
            diverse_recs.append(rec)
            seen_categories.add(rec['category'])
            seen_tags.update(rec['tags'])
            
        return diverse_recs
        
    def _apply_filters(
        self,
        recommendations: List[Dict[str, Any]],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Apply category and tag filters to recommendations."""
        filtered = recommendations
        
        if category:
            filtered = [r for r in filtered if r['category'] == category]
            
        if tags:
            filtered = [r for r in filtered if any(tag in r['tags'] for tag in tags)]
            
        return filtered
        
    def _process_user_features(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user data into features for the model."""
        features = {
            'interactions': [],
            'preferred_categories': set(),
            'preferred_tags': set(),
        }
        
        # Process interactions
        if 'interactions' in user_data:
            features['interactions'] = user_data['interactions']
            
            # Extract category preferences
            for interaction in user_data['interactions']:
                if interaction.get('rating', 0) > 3:  # Consider positive interactions
                    features['preferred_categories'].add(interaction['category'])
                    features['preferred_tags'].update(interaction.get('tags', []))
                    
        return features 