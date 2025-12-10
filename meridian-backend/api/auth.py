"""
Authentication API endpoints.
"""
import os
import json
import uuid
import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

# Google Auth imports (optional - will work without it for mock mode)
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Mock data storage (in-memory for development)
mock_users = {}
active_tokens: dict[str, str] = {}  # token -> user_id


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None


class LoginResponse(BaseModel):
    user: UserResponse
    token: str


class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token (JWT)


def load_google_credentials():
    """Load Google credentials from environment or config file"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id:
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "client_secret_apps.googleusercontent.com.json",
            Path("config") / "client_secret_apps.googleusercontent.com.json",
            Path("../config") / "client_secret_apps.googleusercontent.com.json",
        ]
        
        for config_path in possible_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        web_config = config.get('web', {})
                        client_id = web_config.get('client_id')
                        client_secret = web_config.get('client_secret')
                        break
                except Exception as e:
                    logger.warning(f"Failed to load config file {config_path}: {e}")
    
    return client_id, client_secret


def generate_token() -> str:
    """Generate a mock authentication token"""
    return f"mock_token_{uuid.uuid4().hex[:16]}"


def get_user_from_token(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Extract user from authorization token"""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "")
    user_id = active_tokens.get(token)
    if not user_id:
        return None
    for user in mock_users.values():
        if user["id"] == user_id:
            return user
    return None


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to require authentication"""
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


@router.post("/logout", status_code=200)
async def logout(current_user: dict = Depends(require_auth)):
    """Logout user"""
    return {"message": "Logged out successfully"}


@router.post("/google", response_model=LoginResponse, status_code=200)
async def login_with_google(request: GoogleLoginRequest):
    """Login/Register with Google OAuth"""
    credential = request.credential
    google_client_id, google_client_secret = load_google_credentials()
    
    google_user_info = None
    
    if GOOGLE_AUTH_AVAILABLE and google_client_id:
        try:
            request_obj = requests.Request()
            idinfo = id_token.verify_oauth2_token(
                credential, request_obj, google_client_id
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError(f'Wrong issuer: {idinfo["iss"]}')
            
            google_user_info = {
                'sub': idinfo.get('sub'),
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False),
            }
        except Exception as e:
            logger.warning(f"Google token verification failed: {e}")
            google_user_info = None
    
    # Mock mode: Decode JWT token (basic parsing without verification)
    if not google_user_info:
        try:
            parts = credential.split('.')
            if len(parts) == 3:
                import base64
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded)
                
                google_user_info = {
                    'sub': token_data.get('sub', f'google-user-{uuid.uuid4().hex[:8]}'),
                    'email': token_data.get('email', f'user{uuid.uuid4().hex[:8]}@gmail.com'),
                    'name': token_data.get('name', 'Google User'),
                    'picture': token_data.get('picture'),
                    'email_verified': token_data.get('email_verified', True),
                }
        except Exception as e:
            logger.error(f"Error parsing Google token: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid Google credential: {str(e)}")
    
    if not google_user_info or not google_user_info.get('email'):
        raise HTTPException(status_code=401, detail="Invalid Google credential")
    
    email = google_user_info['email'].lower()
    gcp_user_id = google_user_info['sub']
    name = google_user_info.get('name')
    
    # Find or create user
    user = None
    if email in mock_users:
        user = mock_users[email]
        if not user.get('gcp_user_id'):
            user['gcp_user_id'] = gcp_user_id
            user['gcp_provider'] = 'google'
    else:
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "gcp_user_id": gcp_user_id,
            "gcp_provider": "google",
            "password": None
        }
        mock_users[email] = user
    
    token = generate_token()
    active_tokens[token] = user["id"]
    
    return {
        "user": UserResponse(**{k: v for k, v in user.items() if k != "password"}),
        "token": token
    }

