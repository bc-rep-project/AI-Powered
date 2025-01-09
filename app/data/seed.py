from datetime import datetime, timedelta
import random
from typing import List, Dict

# Sample content categories and tags
CATEGORIES = ["Technology", "Science", "Entertainment", "Sports", "Business", "Health"]
TAGS = {
    "Technology": ["AI", "Programming", "Web Development", "Mobile", "Cloud", "Cybersecurity"],
    "Science": ["Physics", "Biology", "Space", "Chemistry", "Research", "Innovation"],
    "Entertainment": ["Movies", "Music", "Gaming", "TV Shows", "Celebrities", "Arts"],
    "Sports": ["Football", "Basketball", "Tennis", "Soccer", "Olympics", "Fitness"],
    "Business": ["Startups", "Finance", "Marketing", "Leadership", "Innovation", "Strategy"],
    "Health": ["Wellness", "Nutrition", "Mental Health", "Fitness", "Medical", "Healthcare"]
}

# Sample users data
SAMPLE_USERS = [
    {
        "email": "john.doe@example.com",
        "username": "johndoe",
        "preferences": {
            "favorite_categories": ["Technology", "Science"],
            "interests": ["AI", "Space", "Innovation"]
        }
    },
    {
        "email": "jane.smith@example.com",
        "username": "janesmith",
        "preferences": {
            "favorite_categories": ["Health", "Sports"],
            "interests": ["Fitness", "Nutrition", "Wellness"]
        }
    },
    {
        "email": "bob.wilson@example.com",
        "username": "bobwilson",
        "preferences": {
            "favorite_categories": ["Entertainment", "Technology"],
            "interests": ["Gaming", "Programming", "Movies"]
        }
    }
]

# Sample content data
def generate_sample_content(num_items: int = 50) -> List[Dict]:
    content_items = []
    
    for i in range(num_items):
        category = random.choice(CATEGORIES)
        num_tags = random.randint(2, 4)
        tags = random.sample(TAGS[category], num_tags)
        
        created_date = datetime.utcnow() - timedelta(days=random.randint(0, 30))
        
        content_items.append({
            "title": f"Sample Content {i+1}: {category} Article",
            "description": f"This is a sample {category.lower()} article about {', '.join(tags)}.",
            "category": category,
            "tags": tags,
            "metadata": {
                "author": f"Author {random.randint(1, 10)}",
                "read_time": random.randint(3, 15),
                "difficulty_level": random.choice(["Beginner", "Intermediate", "Advanced"]),
                "popularity_score": round(random.uniform(0.1, 1.0), 2)
            },
            "created_at": created_date,
            "updated_at": created_date
        })
    
    return content_items

# Sample interactions data
def generate_sample_interactions(user_ids: List[int], content_ids: List[int], num_interactions: int = 100) -> List[Dict]:
    interactions = []
    
    for _ in range(num_interactions):
        user_id = random.choice(user_ids)
        content_id = random.choice(content_ids)
        interaction_type = random.choice(["view", "like", "share", "bookmark"])
        timestamp = datetime.utcnow() - timedelta(days=random.randint(0, 14))
        
        rating = None
        if interaction_type in ["like", "bookmark"]:
            rating = random.randint(4, 5)
        elif random.random() < 0.3:  # 30% chance of rating for views
            rating = random.randint(1, 5)
        
        interactions.append({
            "user_id": user_id,
            "content_id": content_id,
            "interaction_type": interaction_type,
            "rating": rating,
            "timestamp": timestamp,
            "context": {
                "device": random.choice(["mobile", "desktop", "tablet"]),
                "location": random.choice(["home", "work", "other"]),
                "session_duration": random.randint(30, 900)  # 30 seconds to 15 minutes
            }
        })
    
    return interactions

async def seed_database(db, mongodb):
    """Seed both SQL and MongoDB databases with sample data."""
    try:
        # 1. Create users
        user_ids = []
        for user_data in SAMPLE_USERS:
            user = await db.execute(
                """
                INSERT INTO users (email, username, preferences)
                VALUES (:email, :username, :preferences)
                RETURNING id
                """,
                user_data
            )
            user_ids.append(user.scalar_one())
        
        # 2. Create content
        content_items = generate_sample_content()
        content_ids = []
        for content in content_items:
            result = await db.execute(
                """
                INSERT INTO contents (title, description, metadata)
                VALUES (:title, :description, :metadata)
                RETURNING id
                """,
                content
            )
            content_ids.append(result.scalar_one())
            
            # Store additional content data in MongoDB
            await mongodb.content_items.insert_one({
                "content_id": content_ids[-1],
                "category": content["category"],
                "tags": content["tags"],
                "metadata": content["metadata"],
                "created_at": content["created_at"],
                "updated_at": content["updated_at"]
            })
        
        # 3. Create interactions
        interactions = generate_sample_interactions(user_ids, content_ids)
        for interaction in interactions:
            # Store basic interaction in SQL
            await db.execute(
                """
                INSERT INTO user_interactions (user_id, content_id, interaction_type, rating, timestamp)
                VALUES (:user_id, :content_id, :interaction_type, :rating, :timestamp)
                """,
                interaction
            )
            
            # Store detailed interaction in MongoDB
            await mongodb.user_interactions.insert_one({
                "user_id": interaction["user_id"],
                "content_id": interaction["content_id"],
                "interaction_type": interaction["interaction_type"],
                "rating": interaction["rating"],
                "timestamp": interaction["timestamp"],
                "context": interaction["context"]
            })
        
        await db.commit()
        return True
        
    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        await db.rollback()
        return False 