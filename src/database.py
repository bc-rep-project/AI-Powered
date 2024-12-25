from typing import Optional, Dict
import bcrypt
from datetime import datetime

class Database:
    """Simple in-memory database for development."""
    _users = {}
    _content = {}
    _interactions = {}

    @classmethod
    async def find_user(cls, email: str) -> Optional[Dict]:
        """Find a user by email."""
        return cls._users.get(email)

    @classmethod
    async def create_user(cls, user: Dict) -> Dict:
        """Create a new user."""
        cls._users[user['email']] = user
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password."""
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    @classmethod
    async def get_content(cls, content_id: str) -> Optional[Dict]:
        """Get content by ID."""
        return cls._content.get(content_id)

    @classmethod
    async def add_interaction(cls, user_id: str, content_id: str, interaction_type: str) -> Dict:
        """Add a user-content interaction."""
        interaction = {
            'user_id': user_id,
            'content_id': content_id,
            'interaction_type': interaction_type,
            'timestamp': datetime.utcnow()
        }
        key = f"{user_id}:{content_id}:{interaction_type}"
        cls._interactions[key] = interaction
        return interaction

    @classmethod
    async def get_user_interactions(cls, user_id: str) -> list:
        """Get all interactions for a user."""
        return [
            interaction for interaction in cls._interactions.values()
            if interaction['user_id'] == user_id
        ] 