from typing import Dict, Optional
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi import HTTPException

config = Config('.env')

oauth = OAuth(config)

# Google OAuth setup
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=config('GOOGLE_CLIENT_ID', default=None),
    client_secret=config('GOOGLE_CLIENT_SECRET', default=None),
    client_kwargs={
        'scope': 'openid email profile'
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

async def get_oauth_user_data(provider: str, token: Dict) -> Dict:
    """Get user data from OAuth provider."""
    if provider == 'google':
        client = oauth.google
        resp = await client.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
        profile = resp.json()
        return {
            'email': profile['email'],
            'username': profile.get('name', profile['email'].split('@')[0]),
            'picture': profile.get('picture'),
            'provider': 'google'
        }
    elif provider == 'github':
        client = oauth.github
        resp = await client.get('user', token=token)
        profile = resp.json()
        # Get primary email since it might be private
        emails_resp = await client.get('user/emails', token=token)
        emails = emails_resp.json()
        primary_email = next(email['email'] for email in emails if email['primary'])
        return {
            'email': primary_email,
            'username': profile.get('login'),
            'picture': profile.get('avatar_url'),
            'provider': 'github'
        }
    elif provider == 'facebook':
        client = oauth.facebook
        # Get user data including email
        resp = await client.get(
            'me',
            token=token,
            params={'fields': 'id,name,email,picture.type(large)'}
        )
        profile = resp.json()
        return {
            'email': profile['email'],
            'username': profile.get('name').replace(' ', '_').lower(),
            'picture': profile.get('picture', {}).get('data', {}).get('url'),
            'provider': 'facebook'
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

def get_oauth_redirect_uri(provider: str, request_base_url: str) -> str:
    """Get OAuth redirect URI based on the provider."""
    return f"{request_base_url}api/v1/auth/{provider}/callback" 