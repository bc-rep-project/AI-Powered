from app.repositories.supabase_repository import SupabaseRepository
from app.models.sql_models import User, Content, UserInteraction

class DatabaseService:
    def __init__(self):
        self.repo = SupabaseRepository()
    
    async def create_user(self, email: str, username: str, preferences: dict = None) -> User:
        user = User(
            email=email,
            username=username,
            preferences=preferences or {}
        )
        return await self.repo.create_user(user)
    
    async def record_interaction(
        self,
        user_id: int,
        content_id: int,
        interaction_type: str,
        rating: float = None
    ) -> UserInteraction:
        interaction = UserInteraction(
            user_id=user_id,
            content_id=content_id,
            interaction_type=interaction_type,
            rating=rating
        )
        return await self.repo.store_interaction(interaction) 