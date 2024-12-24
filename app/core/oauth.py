from typing import Dict, Optional
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi import HTTPException
import os
import secrets
from starlette.responses import RedirectResponse
import logging

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

def handle_oauth_callback(provider: str, user_data: dict, access_token: str) -> RedirectResponse:
    """Handle OAuth callback and redirect to frontend."""
    try:
        frontend_url = os.getenv('FRONTEND_URL', 'https://ai-powered-content-recommendation-frontend.vercel.app')
        
        # Log the redirect attempt
        logger.info(f"Redirecting to frontend with user data: {user_data}")
        
        # Construct redirect URL with token and user data
        redirect_url = (
            f"{frontend_url}/dashboard"
            f"?access_token={access_token}"
            f"&user={user_data['email']}"
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