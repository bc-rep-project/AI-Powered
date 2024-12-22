from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks, Form
from fastapi.security import OAuth2PasswordRequestForm
from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.core.oauth import oauth, get_oauth_user_data, get_oauth_redirect_uri
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

@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow."""
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider. Supported providers: {', '.join(SUPPORTED_OAUTH_PROVIDERS)}"
        )
    
    redirect_uri = get_oauth_redirect_uri(provider, str(request.base_url))
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)

@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle OAuth callback."""
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider. Supported providers: {', '.join(SUPPORTED_OAUTH_PROVIDERS)}"
        )
    
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    user_data = await get_oauth_user_data(provider, token)
    
    # Check if user exists
    db_user = db.query(User).filter(User.email == user_data['email']).first()
    
    if not db_user:
        # Create new user
        db_user = User(
            email=user_data['email'],
            username=user_data['username'],
            hashed_password=None,  # OAuth users don't have passwords
            picture=user_data.get('picture'),
            oauth_provider=provider
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    elif db_user.oauth_provider != provider:
        # If user exists but with different provider, update the provider
        db_user.oauth_provider = provider
        db_user.picture = user_data.get('picture')
        db.commit()
        db.refresh(db_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": db_user.email})
    
    # Return token via post message to parent window
    html_content = f"""
        <html>
            <body>
                <script>
                    window.opener.postMessage(
                        {{
                            type: 'social_auth_success',
                            token: '{access_token}'
                        }},
                        '*'
                    );
                    window.close();
                </script>
            </body>
        </html>
    """
    return Response(content=html_content, media_type="text/html")

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