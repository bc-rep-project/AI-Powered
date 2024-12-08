from pydantic import BaseModel
from datetime import datetime

class UserInteraction(BaseModel):
    user_id: int
    content_id: int
    interaction_type: str  # view, click, share
    timestamp: datetime
    context: dict  # device, location, etc.

class ViewingSession(BaseModel):
    user_id: int
    content_id: int
    start_time: datetime
    end_time: datetime
    watch_duration: int
    device_info: dict 