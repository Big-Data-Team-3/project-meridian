"""
Authentication API endpoints.
"""
import os
import json
import uuid
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Header, Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text

# Google Auth imports (optional - will work without it for mock mode)
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

from database.cloud_sql_client import get_db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Security scheme for FastAPI docs (shows the lock icon and Authorization field)
bearer_scheme = HTTPBearer(auto_error=False)

# Database client (lazy initialization)
_db_client = None


def get_db_client_instance():
    """
    Get or create database client instance.
    Note: This does NOT establish a connection - connection is lazy.
    """
    global _db_client
    if _db_client is None:
        try:
            _db_client = get_db_client()
        except Exception as e:
            logger.error(f"Failed to initialize database client: {e}", exc_info=True)
            raise
    return _db_client


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


def get_user_from_token(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Extract user from authorization token by querying auth_credentials table.
    The token is the credential_id from auth_credentials.
    """
    if not authorization:
        return None
    
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    
    try:
        db_client = get_db_client_instance()
        query = text("""
            SELECT 
                u.user_id,
                u.email,
                u.name,
                u.gcp_user_id,
                u.gcp_provider,
                u.is_active,
                u.is_verified
            FROM meridian.auth_credentials ac
            JOIN meridian.users u ON u.user_id = ac.user_id
            WHERE ac.credential_id = :credential_id
              AND ac.is_active = TRUE
              AND u.is_active = TRUE
              AND (ac.expires_at IS NULL OR ac.expires_at > CURRENT_TIMESTAMP)
              AND ac.revoked_at IS NULL
        """)
        
        with db_client.get_connection() as conn:
            result = conn.execute(query, {"credential_id": token})
            row = result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),  # user_id
                    "email": row[1],
                    "name": row[2],
                    "gcp_user_id": row[3],
                    "gcp_provider": row[4],
                    "is_active": row[5],
                    "is_verified": row[6]
                }
    except Exception as e:
        # Log the error but don't raise - let require_auth handle it
        # This allows us to distinguish between "no user found" vs "database error"
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ['database', 'connection', 'sql', 'postgres', 'pg8000', 'operational']):
            # Re-raise database errors so require_auth can handle them properly
            logger.error(f"Database error getting user from token: {e}", exc_info=True)
            raise
        else:
            # For other errors, log and return None (will result in 401)
            logger.error(f"Error getting user from token: {e}", exc_info=True)
    
    return None


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """
    Dependency to require authentication.
    Returns user dict if authenticated, raises 401 if not.
    Handles database errors gracefully.

    Note: Using HTTPBearer + Security so the Swagger UI shows an
    Authorization input (lock icon) and sends the Bearer token automatically.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Unauthorized: No authorization token provided")

    authorization = f"Bearer {credentials.credentials}"
    
    try:
        user = get_user_from_token(authorization)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or expired token")
        return user
    except HTTPException:
        # Re-raise HTTP exceptions (like 401)
        raise
    except Exception as e:
        # Handle database connection errors and other unexpected errors
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ['database', 'connection', 'sql', 'postgres', 'pg8000']):
            logger.error(f"Database error in require_auth: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable: Database connection error"
            )
        else:
            logger.error(f"Unexpected error in require_auth: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Internal server error during authentication"
            )


@router.post("/logout", status_code=200)
async def logout(
    current_user: dict = Depends(require_auth),
    authorization: Optional[str] = Header(None)
):
    """
    Logout user by revoking the current session token.
    Sets revoked_at timestamp and is_active = FALSE for the credential.
    """
    if not authorization:
        return {"message": "Logged out successfully"}
    
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return {"message": "Logged out successfully"}
    
    try:
        db_client = get_db_client_instance()
        query = text("""
            UPDATE meridian.auth_credentials
            SET 
                is_active = FALSE,
                revoked_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE credential_id = :credential_id
              AND user_id = :user_id
              AND is_active = TRUE
        """)
        
        with db_client.get_connection() as conn:
            conn.execute(query, {
                "credential_id": token,
                "user_id": current_user["id"]
            })
            conn.commit()
    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        # Continue with logout even if database update fails
    
    return {"message": "Logged out successfully"}


@router.post("/google", response_model=LoginResponse, status_code=200)
async def login_with_google(
    request: GoogleLoginRequest,
    http_request: Request
):
    """
    Login/Register with Google OAuth.
    
    Flow:
    1. Verify Google ID token
    2. Find or create user in meridian.users table
    3. Insert token information into meridian.auth_credentials table
    4. Return user info and session token (credential_id)
    """
    credential = request.credential
    google_client_id, google_client_secret = load_google_credentials()
    
    google_user_info = None
    
    # Try to verify Google token if available
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
                'exp': idinfo.get('exp'),  # Token expiration
            }
        except Exception as e:
            logger.warning(f"Google token verification failed: {e}")
            google_user_info = None
    
    # Fallback: Decode JWT token (basic parsing without verification)
    # This is for development/testing when Google auth libraries aren't available
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
                    'exp': token_data.get('exp'),
                }
        except Exception as e:
            logger.error(f"Error parsing Google token: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid Google credential: {str(e)}")
    
    if not google_user_info or not google_user_info.get('email'):
        raise HTTPException(status_code=401, detail="Invalid Google credential")
    
    email = google_user_info['email'].lower()
    gcp_user_id = google_user_info['sub']
    name = google_user_info.get('name')
    email_verified = google_user_info.get('email_verified', False)
    
    # Calculate token expiration
    expires_at = None
    if google_user_info.get('exp'):
        try:
            expires_at = datetime.fromtimestamp(google_user_info['exp'])
        except (ValueError, TypeError):
            # Default to 1 hour from now if exp is invalid
            expires_at = datetime.utcnow() + timedelta(hours=1)
    
    # Get client info for auth_credentials
    user_agent = http_request.headers.get('user-agent', '')
    client_ip = http_request.client.host if http_request.client else None
    
    try:
        db_client = get_db_client_instance()
        
        # Step 1: Find or create user
        user = None
        with db_client.get_connection() as conn:
            # Try to find user by gcp_user_id first, then by email
            find_user_query = text("""
                SELECT user_id, email, name, gcp_user_id, gcp_provider, is_active, is_verified
                FROM meridian.users
                WHERE gcp_user_id = :gcp_user_id OR email = :email
                LIMIT 1
            """)
            
            result = conn.execute(find_user_query, {
                "gcp_user_id": gcp_user_id,
                "email": email
            })
            row = result.fetchone()
            
            if row:
                # User exists - update last_login_at and gcp fields if needed
                user_id = str(row[0])
                update_user_query = text("""
                    UPDATE meridian.users
                    SET 
                        last_login_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP,
                        gcp_user_id = COALESCE(:gcp_user_id, gcp_user_id),
                        gcp_email = COALESCE(:gcp_email, gcp_email),
                        gcp_provider = COALESCE(:gcp_provider, gcp_provider),
                        is_verified = :is_verified,
                        name = COALESCE(:name, name)
                    WHERE user_id = :user_id
                    RETURNING user_id, email, name, gcp_user_id, gcp_provider, is_active, is_verified
                """)
                
                result = conn.execute(update_user_query, {
                    "user_id": user_id,
                    "gcp_user_id": gcp_user_id,
                    "gcp_email": email,
                    "gcp_provider": "google",
                    "is_verified": email_verified,
                    "name": name
                })
                updated_row = result.fetchone()
                conn.commit()
                
                user = {
                    "id": str(updated_row[0]),
                    "email": updated_row[1],
                    "name": updated_row[2],
                    "gcp_user_id": updated_row[3],
                    "gcp_provider": updated_row[4],
                    "is_active": updated_row[5],
                    "is_verified": updated_row[6]
                }
            else: # if user not found, create new user
                new_user_id = uuid.uuid4()
                create_user_query = text("""
                    INSERT INTO meridian.users 
                        (user_id, email, name, gcp_user_id, gcp_email, gcp_provider, 
                         is_active, is_verified, created_at, updated_at, last_login_at)
                    VALUES 
                        (:user_id, :email, :name, :gcp_user_id, :gcp_email, :gcp_provider,
                         :is_active, :is_verified, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING user_id, email, name, gcp_user_id, gcp_provider, is_active, is_verified
                """)
                
                result = conn.execute(create_user_query, {
                    "user_id": str(new_user_id),
                    "email": email,
                    "name": name,
                    "gcp_user_id": gcp_user_id,
                    "gcp_email": email,
                    "gcp_provider": "google",
                    "is_active": True,
                    "is_verified": email_verified
                })
                new_row = result.fetchone()
                conn.commit()
                
                if not new_row:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create new user: INSERT did not return a row"
                    )
                
                user = {
                    "id": str(new_row[0]),
                    "email": new_row[1],
                    "name": new_row[2],
                    "gcp_user_id": new_row[3],
                    "gcp_provider": new_row[4],
                    "is_active": new_row[5],
                    "is_verified": new_row[6]
                }
            
            # Step 2: Insert auth credentials
            credential_id = uuid.uuid4()
            insert_credential_query = text("""
                INSERT INTO meridian.auth_credentials
                    (credential_id, user_id, id_token, auth_provider, provider_user_id, 
                     provider_email, expires_at, user_agent, ip_address, is_active)
                VALUES
                    (:credential_id, :user_id, :id_token, :auth_provider, :provider_user_id,
                     :provider_email, :expires_at, :user_agent, :ip_address, :is_active)
                RETURNING credential_id
            """)
            
            result = conn.execute(insert_credential_query, {
                "credential_id": str(credential_id),
                "user_id": user["id"],
                "id_token": credential,  # Store the Google ID token
                "auth_provider": "google",
                "provider_user_id": gcp_user_id,
                "provider_email": email,
                "expires_at": expires_at,
                "user_agent": user_agent,
                "ip_address": client_ip,
                "is_active": True
            })
            conn.commit()
            
            # Use credential_id as the session token
            session_token = str(credential_id)
    
        return {
                "user": UserResponse(
                    id=user["id"],
                    email=user["email"],
                    name=user["name"]
                ),
                "token": session_token
        }
        
    except Exception as e:
        logger.error(f"Database error during Google login: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process login: {str(e)}"
        )

