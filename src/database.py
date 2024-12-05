from motor.motor_asyncio import AsyncIOMotorClient
import os
from typing import Optional
from datetime import datetime, timedelta

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB"""
        cls.client = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
        cls.db = cls.client.recommendation_db
        
        # Create indexes
        await cls._create_indexes()
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
    
    @classmethod
    async def _create_indexes(cls):
        """Create database indexes"""
        # Users collection indexes
        await cls.db.users.create_index("email", unique=True)
        await cls.db.users.create_index("id", unique=True)
        
        # Content collection indexes
        await cls.db.content.create_index("id", unique=True)
        await cls.db.content.create_index("type")
        await cls.db.content.create_index("tags")
        await cls.db.content.create_index([("title", "text"), ("description", "text")])
        
        # Interactions collection indexes
        await cls.db.interactions.create_index("user_id")
        await cls.db.interactions.create_index("content_id")
        await cls.db.interactions.create_index([("user_id", 1), ("content_id", 1)])
        await cls.db.interactions.create_index("timestamp")
        
        # Recommendation history indexes
        await cls.db.recommendation_history.create_index("user_id")
        await cls.db.recommendation_history.create_index("timestamp")
        
        # Metrics collection indexes
        await cls.db.metrics.create_index("user_id")
        await cls.db.metrics.create_index("timestamp")
        await cls.db.metrics.create_index([("user_id", 1), ("timestamp", 1)])
        
        # A/B testing indexes
        await cls.db.ab_tests.create_index("name", unique=True)
        await cls.db.ab_tests.create_index("status")
        await cls.db.user_variants.create_index([("user_id", 1), ("test_name", 1)], unique=True)
    
    @classmethod
    async def get_trending_content(cls, limit: int = 10, time_window_hours: int = 24):
        """Get trending content based on recent interactions"""
        pipeline = [
            {
                "$match": {
                    "timestamp": {
                        "$gte": datetime.utcnow() - timedelta(hours=time_window_hours)
                    }
                }
            },
            {
                "$group": {
                    "_id": "$content_id",
                    "interaction_count": {"$sum": 1},
                    "weighted_score": {
                        "$sum": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$interaction_type", "view"]}, "then": 1},
                                    {"case": {"$eq": ["$interaction_type", "click"]}, "then": 2},
                                    {"case": {"$eq": ["$interaction_type", "like"]}, "then": 3},
                                    {"case": {"$eq": ["$interaction_type", "share"]}, "then": 4},
                                    {"case": {"$eq": ["$interaction_type", "purchase"]}, "then": 5}
                                ],
                                "default": 1
                            }
                        }
                    }
                }
            },
            {"$sort": {"weighted_score": -1}},
            {"$limit": limit}
        ]
        
        trending_ids = await cls.db.interactions.aggregate(pipeline).to_list(limit)
        content_ids = [item["_id"] for item in trending_ids]
        
        if not content_ids:
            return []
            
        trending_content = await cls.db.content.find({"id": {"$in": content_ids}}).to_list(limit)
        return trending_content
    
    @classmethod
    async def get_category_recommendations(cls, user_id: str, category: str, limit: int = 5):
        """Get recommendations within a specific category"""
        # Get user's preferred content in the category
        user_interactions = await cls.db.interactions.find({
            "user_id": user_id,
            "content_id": {
                "$in": await cls.db.content.distinct("id", {"type": category})
            }
        }).sort("timestamp", -1).to_list(100)
        
        if not user_interactions:
            # Return popular items in category if no user history
            return await cls.db.content.find({"type": category}).sort(
                "interaction_count", -1
            ).limit(limit).to_list(limit)
        
        # Get similar content based on user's interaction history
        content_ids = [interaction["content_id"] for interaction in user_interactions]
        similar_content = await cls.db.content.find({
            "type": category,
            "id": {"$nin": content_ids}  # Exclude already interacted content
        }).limit(limit).to_list(limit)
        
        return similar_content 