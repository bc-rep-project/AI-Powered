import os
from supabase import create_client, Client
from app.core.config import settings

class SupabaseClient:
    def __init__(self):
        self.supabase: Client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY
        )
    
    async def get_client(self) -> Client:
        return self.supabase

supabase_client = SupabaseClient() 