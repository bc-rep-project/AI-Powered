from typing import List, Optional
from app.db.supabase_client import supabase_client
from app.models.sql_models import User, Content, UserInteraction

class SupabaseRepository:
    def __init__(self):
        self.client = supabase_client.get_client()
    
    async def create_user(self, user: User) -> dict:
        response = await self.client.table('users').insert({
            'email': user.email,
            'username': user.username,
            'preferences': user.preferences
        }).execute()
        return response.data[0]
    
    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        response = await self.client.table('users')\
            .select('*')\
            .eq('id', user_id)\
            .single()\
            .execute()
        return response.data
    
    async def store_interaction(self, interaction: UserInteraction) -> dict:
        response = await self.client.table('user_interactions').insert({
            'user_id': interaction.user_id,
            'content_id': interaction.content_id,
            'interaction_type': interaction.interaction_type,
            'rating': interaction.rating
        }).execute()
        return response.data[0]
    
    async def get_user_recommendations(self, user_id: int, limit: int = 10) -> List[dict]:
        response = await self.client.table('contents')\
            .select('*')\
            .limit(limit)\
            .execute()
        return response.data 