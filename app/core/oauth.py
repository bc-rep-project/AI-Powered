from typing import Dict, Optional
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi import HTTPException
import os
import secrets
from starlette.responses import RedirectResponse
import logging
from datetime import datetime
from app.core.auth import create_access_token
from app.db.database import mongodb

logger = logging.getLogger(__name__)

config = Config('.env')

oauth = OAuth(config)

FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://ai-powered-content-recommendation-frontend.vercel.app')

# Google OAuth setup
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'
    }
)

# GitHub OAuth setup
oauth.register(
    name='github',
    client_id=config('GITHUB_CLIENT_ID', default=None),
    client_secret=config('GITHUB_CLIENT_SECRET', default=None),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Facebook OAuth setup
oauth.register(
    name='facebook',
    client_id=config('FACEBOOK_CLIENT_ID', default=None),
    client_secret=config('FACEBOOK_CLIENT_SECRET', default=None),
    access_token_url='https://graph.facebook.com/oauth/access_token',
    access_token_params=None,
    authorize_url='https://www.facebook.com/dialog/oauth',
    authorize_params=None,
    api_base_url='https://graph.facebook.com/',
    client_kwargs={
        'scope': 'email,public_profile',
        'response_type': 'code',
    },
)

async def get_oauth_user_data(provider: str, token: dict) -> dict:
    """Get user data from OAuth provider."""
    try:
        if provider == 'google':
            # Get user info from Google
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            if resp.status_code != 200:
                logger.error(f"Failed to get user info from Google. Status: {resp.status_code}")
                raise HTTPException(status_code=400, detail="Failed to get user info from Google")
                
            user_info = resp.json()
            logger.info(f"Received user info from Google: {user_info}")
            
            return {
                "email": user_info.get('email'),
                "username": user_info.get('name'),
                "picture": user_info.get('picture'),
                "provider": "google"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")
            
    except Exception as e:
        logger.error(f"Error getting OAuth user data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user data from {provider}")

def get_oauth_redirect_uri(provider: str, base_url: str) -> str:
    """Get the OAuth redirect URI for the specified provider."""
    return f"https://ai-recommendation-api.onrender.com/api/v1/auth/{provider}/callback"

def generate_state_token() -> str:
    """Generate a secure state token for OAuth."""
    return secrets.token_urlsafe(32)

async def handle_oauth_callback(provider: str, user_data: dict, access_token: str) -> RedirectResponse:
    """Handle OAuth callback and redirect to frontend."""
    try:
        # Create or update user in database
        db_user = await create_or_update_oauth_user(user_data)
        
        # Generate JWT token
        jwt_token = create_access_token(
            data={"sub": db_user["email"], "user_id": str(db_user["_id"])}
        )
        
        # Log the redirect attempt
        logger.info(f"Redirecting to frontend with user data: {user_data}")
        
        # Construct redirect URL with token and user data
        redirect_url = (
            f"{FRONTEND_URL}/dashboard"
            f"?access_token={jwt_token}"
            f"&email={user_data['email']}"
            f"&provider={provider}"
        )
        
        # Use 302 status code for temporary redirect
        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"Error handling OAuth callback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to handle OAuth callback") 

async def create_or_update_oauth_user(user_data: dict) -> dict:
    """Create or update user from OAuth data."""
    try:
        # Check if user exists
        existing_user = await mongodb.db.users.find_one({"email": user_data["email"]})
        
        if existing_user:
            # Update existing user
            update_data = {
                "$set": {
                    "last_login": datetime.utcnow(),
                    "picture": user_data.get("picture"),
                    "provider": user_data.get("provider")
                }
            }
            await mongodb.db.users.update_one(
                {"email": user_data["email"]},
                update_data
            )
            return existing_user
            
        # Create new user
        new_user = {
            "email": user_data["email"],
            "username": user_data["username"],
            "picture": user_data.get("picture"),
            "provider": user_data.get("provider"),
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        
        result = await mongodb.db.users.insert_one(new_user)
        new_user["_id"] = result.inserted_id
        return new_user
        
    except Exception as e:
        logger.error(f"Error creating/updating OAuth user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error creating/updating user account"
        ) 