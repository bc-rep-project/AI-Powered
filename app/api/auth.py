from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks, Form
from fastapi.security import OAuth2PasswordRequestForm
from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_password
)
from app.core.oauth import oauth, get_oauth_user_data, get_oauth_redirect_uri, generate_state_token, handle_oauth_callback
from app.models.user import User, UserCreate, Token, PasswordReset
from app.db.database import mongodb
import uuid
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, RedirectResponse
from typing import Optional, Any
import secrets
from datetime import datetime, timedelta
from app.core.db import get_db
from app.core.monitoring import metrics_logger
import logging
from pydantic import BaseModel, EmailStr
from passlib.hash import bcrypt
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

SUPPORTED_OAUTH_PROVIDERS = ['google', 'github', 'facebook']

# Keep track of reset tokens
reset_tokens = {}  # token -> {user_id, expiry}

class UserRegister(BaseModel):
    username: str
    email: EmailStr  # This ensures email validation
    password: str

@router.post("/register", status_code=201)
async def register(user: UserRegister):
    try:
        logger.info(f"Registration attempt for email: {user.email}")
        
        # Check if email exists
        existing_email = await mongodb.db.users.find_one({"email": user.email})
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
            
        # Check if username exists
        existing_username = await mongodb.db.users.find_one({"username": user.username})
        if existing_username:
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
            
        # Hash password and create user
        hashed_password = get_password_hash(user.password)
        new_user = {
            "username": user.username,
            "email": user.email,
            "password": hashed_password,
            "created_at": datetime.utcnow()
        }
        
        await mongodb.db.users.insert_one(new_user)
        logger.info(f"Successfully registered user: {user.email}")
        
        return {
            "message": "User registered successfully",
            "email": user.email
        }
        
    except HTTPException as he:
        logger.error(f"Registration failed: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during registration"
        )

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
) -> Any:
    logger.info(f"Login attempt for user: {username}")
    try:
        user = await authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token = create_access_token(data={"sub": user.email})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user 

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    try:
        user = await mongodb.db.users.find_one({"email": form_data.username})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        if not verify_password(form_data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        access_token = create_access_token(data={"sub": user["email"]})
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise

@router.get("/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow."""
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider. Supported providers: {', '.join(SUPPORTED_OAUTH_PROVIDERS)}"
        )
    
    try:
        redirect_uri = get_oauth_redirect_uri(provider, str(request.base_url))
        state = generate_state_token()
        request.session['oauth_state'] = state
        
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(status_code=400, detail=f"OAuth client for {provider} not properly configured")
            
        return await client.authorize_redirect(request, redirect_uri, state=state)
    except Exception as e:
        logger.error(f"OAuth login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth login failed: {str(e)}")

@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request):
    """Handle OAuth callback."""
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider. Supported providers: {', '.join(SUPPORTED_OAUTH_PROVIDERS)}"
        )
    
    try:
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(status_code=400, detail=f"OAuth client for {provider} not properly configured")
            
        token = await client.authorize_access_token(request)
        if not token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
            
        user_data = await get_oauth_user_data(provider, token)
        return handle_oauth_callback(provider, user_data, token.get('access_token'))
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Initiate password reset process."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If an account exists with this email, you will receive a password reset link"}
    
    # Generate reset token
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    # Store token
    reset_tokens[token] = {
        "user_id": user.id,
        "expiry": expiry
    }
    
    # Send reset email
    reset_link = f"{request.base_url}reset-password?token={token}"
    background_tasks.add_task(
        send_reset_password_email,
        email=user.email,
        username=user.username,
        reset_link=reset_link
    )
    
    return {"message": "If an account exists with this email, you will receive a password reset link"}

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password using token."""
    token_data = reset_tokens.get(reset_data.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if datetime.utcnow() > token_data["expiry"]:
        # Clean up expired token
        del reset_tokens[reset_data.token]
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Get user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    db.commit()
    
    # Clean up used token
    del reset_tokens[reset_data.token]
    
    return {"message": "Password has been reset successfully"}

@router.post("/validate-reset-token")
async def validate_reset_token(token: str):
    """Validate a password reset token."""
    token_data = reset_tokens.get(token)
    if not token_data or datetime.utcnow() > token_data["expiry"]:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {"message": "Token is valid"}

def get_password_hash(password: str) -> str:
    return bcrypt.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)

@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OAuth login flow"""
    redirect_uri = get_oauth_redirect_uri('google', str(request.base_url))
    state = generate_state_token()
    request.session['oauth_state'] = state
    return await oauth.google.authorize_redirect(request, redirect_uri, state=state)

@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        # Get the authorization code from the request
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
            
        # Verify state if it was stored in session
        if 'oauth_state' in request.session:
            if state != request.session['oauth_state']:
                raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Exchange the authorization code for an access token
        token = await oauth.google.authorize_access_token(request)
        if not token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
            
        # Get user info from Google
        user_data = await get_oauth_user_data('google', token)
        
        # Create or update user in database
        db_user = await create_or_update_oauth_user(user_data)
        
        # Generate JWT token
        access_token = create_access_token(
            data={"sub": db_user["email"], "user_id": str(db_user["_id"])}
        )
        
        # Construct frontend URL with token
        frontend_url = os.getenv('FRONTEND_URL', 'https://ai-powered-content-recommendation-frontend.vercel.app')
        redirect_url = f"{frontend_url}/dashboard?access_token={access_token}&user={user_data['email']}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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