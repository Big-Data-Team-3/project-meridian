"""
Meridian Backend API Server with Dummy Endpoints
All endpoints return 200 status codes with mock data for development
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, List
from datetime import datetime, timedelta
import uvicorn
import os
import uuid
import random
import json
from pathlib import Path

# Google Auth imports (optional - will work without it for mock mode)
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    print("⚠️  google-auth library not installed. Google OAuth will work in mock mode only.")
    print("   Install with: pip install google-auth")

def load_google_credentials():
    """Load Google credentials from environment or config file"""
    # Try environment variables first
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # If not in environment, try to load from config file
    if not client_id:
        # Try multiple possible paths
        possible_paths = [
            Path(__file__).parent.parent / "config" / "client_secret_apps.googleusercontent.com.json",
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
                        print(f"✅ Loaded Google credentials from: {config_path}")
                        print(f"   Client ID: {client_id[:30] if client_id else 'None'}...")
                        break
                except Exception as e:
                    print(f"⚠️  Failed to load config file {config_path}: {e}")
    
    return client_id, client_secret

app = FastAPI(title="Meridian Backend API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    email: str
    password: str
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

class LoginResponse(BaseModel):
    user: UserResponse
    token: str

class MessageRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: datetime
    conversationId: str

class SendMessageResponse(BaseModel):
    message: MessageResponse
    conversationId: str

class ConversationResponse(BaseModel):
    id: str
    title: str
    createdAt: datetime
    updatedAt: datetime
    messageCount: int

class CreateConversationRequest(BaseModel):
    title: Optional[str] = None

class CreateConversationResponse(BaseModel):
    conversation: ConversationResponse

class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token (JWT)

class HealthResponse(BaseModel):
    status: str
    message: Optional[str] = None
    service: Optional[str] = None

# ============================================================================
# Mock Data Storage (In-memory for development)
# ============================================================================

# Mock users database
mock_users = {
    "user1@example.com": {
        "id": "user-1",
        "email": "user1@example.com",
        "name": "John Doe",
        "password": "password123"  # In production, use hashed passwords
    },
    "demo@meridian.com": {
        "id": "user-demo",
        "email": "demo@meridian.com",
        "name": "Demo User",
        "password": "demo123"
    }
}

# Mock conversations storage
mock_conversations: dict[str, ConversationResponse] = {}
mock_messages: dict[str, List[MessageResponse]] = {}

# Mock tokens (in production, use JWT)
active_tokens: dict[str, str] = {}  # token -> user_id

# ============================================================================
# Helper Functions
# ============================================================================

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
    # Find user by ID
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

# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def root():
    """Root health check endpoint"""
    return {
        "status": "ok",
        "message": "Meridian Backend API is running"
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy"}

@app.get("/api/health", response_model=HealthResponse)
async def api_health():
    """API health check endpoint"""
    return {
        "status": "ok",
        "service": "meridian-backend"
    }

# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/register", response_model=LoginResponse, status_code=200)
async def register(request: RegisterRequest):
    """Register a new user"""
    # Check if user already exists
    if request.email in mock_users:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    new_user = {
        "id": user_id,
        "email": request.email,
        "name": request.name,
        "password": request.password  # In production, hash this
    }
    mock_users[request.email] = new_user
    
    # Generate token
    token = generate_token()
    active_tokens[token] = user_id
    
    return {
        "user": UserResponse(**new_user),
        "token": token
    }

@app.post("/api/auth/login", response_model=LoginResponse, status_code=200)
async def login(request: LoginRequest):
    """Login user"""
    user = mock_users.get(request.email)
    
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    token = generate_token()
    active_tokens[token] = user["id"]
    
    return {
        "user": UserResponse(**{k: v for k, v in user.items() if k != "password"}),
        "token": token
    }

@app.post("/api/auth/logout", status_code=200)
async def logout(current_user: dict = Depends(require_auth)):
    """Logout user"""
    # In a real implementation, invalidate the token
    # For mock, we'll just return success
    return {"message": "Logged out successfully"}

@app.post("/api/auth/google", response_model=LoginResponse, status_code=200)
async def login_with_google(request: GoogleLoginRequest):
    """Login/Register with Google OAuth"""
    print("=" * 60)
    print("🔵 BACKEND: Google Authentication Request Received")
    print("=" * 60)
    
    credential = request.credential
    print(f"   Credential length: {len(credential) if credential else 0}")
    print(f"   Credential preview: {credential[:50] if credential else 'None'}...")
    
    # Load Google credentials (from env or config file)
    google_client_id, google_client_secret = load_google_credentials()
    print(f"   GOOGLE_CLIENT_ID set: {bool(google_client_id)}")
    if google_client_id:
        print(f"   GOOGLE_CLIENT_ID: {google_client_id[:30]}...")
    print(f"   GOOGLE_CLIENT_SECRET set: {bool(google_client_secret)}")
    print(f"   GOOGLE_AUTH_AVAILABLE: {GOOGLE_AUTH_AVAILABLE}")
    
    # Note: Client secret is not needed for ID token verification
    # It's only needed for OAuth 2.0 authorization code flow
    # For Google Identity Services (One Tap), we only need Client ID
    
    # Verify Google ID token
    google_user_info = None
    
    if GOOGLE_AUTH_AVAILABLE and google_client_id:
        try:
            print("   Attempting to verify token with Google...")
            # Verify the token with Google
            # Note: Only Client ID is needed, NOT client secret for ID token verification
            # Client secret is only needed for OAuth 2.0 authorization code flow
            request_obj = requests.Request()
            idinfo = id_token.verify_oauth2_token(
                credential, request_obj, google_client_id
            )
            
            print(f"   ✅ Token verified successfully!")
            print(f"   Issuer: {idinfo.get('iss')}")
            print(f"   Audience: {idinfo.get('aud')}")
            print(f"   Subject (user ID): {idinfo.get('sub')}")
            print(f"   Email: {idinfo.get('email')}")
            
            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError(f'Wrong issuer: {idinfo["iss"]}')
            
            # Verify the audience (should match Client ID)
            if idinfo.get('aud') != google_client_id:
                print(f"⚠️  Audience mismatch: expected {google_client_id}, got {idinfo.get('aud')}")
                # Still proceed, but log the warning
            
            google_user_info = {
                'sub': idinfo.get('sub'),  # Google user ID
                'email': idinfo.get('email'),
                'name': idinfo.get('name'),
                'picture': idinfo.get('picture'),
                'email_verified': idinfo.get('email_verified', False),
            }
            print(f"✅ Token verification successful - using verified user info")
        except Exception as e:
            # If verification fails, use mock mode for development
            print(f"⚠️  Google token verification failed: {type(e).__name__}: {e}")
            print("   Using mock mode for development")
            import traceback
            traceback.print_exc()
            google_user_info = None
    
    # Mock mode: Decode JWT token (basic parsing without verification)
    if not google_user_info:
        print("   Using mock mode (JWT parsing without verification)")
        try:
            # Basic JWT parsing (for development only - NOT secure!)
            parts = credential.split('.')
            print(f"   JWT parts count: {len(parts)}")
            if len(parts) == 3:
                import base64
                # Decode payload (second part)
                payload = parts[1]
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded)
                print(f"   Decoded token data keys: {list(token_data.keys())}")
                
                google_user_info = {
                    'sub': token_data.get('sub', f'google-user-{uuid.uuid4().hex[:8]}'),
                    'email': token_data.get('email', f'user{uuid.uuid4().hex[:8]}@gmail.com'),
                    'name': token_data.get('name', 'Google User'),
                    'picture': token_data.get('picture'),
                    'email_verified': token_data.get('email_verified', True),
                }
                print(f"   Extracted user info: email={google_user_info.get('email')}, sub={google_user_info.get('sub')}")
        except Exception as e:
            print(f"❌ Error parsing Google token: {e}")
            import traceback
            traceback.print_exc()
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
        # Update GCP info if not set
        if not user.get('gcp_user_id'):
            user['gcp_user_id'] = gcp_user_id
            user['gcp_provider'] = 'google'
    else:
        # Create new user
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        user = {
            "id": user_id,
            "email": email,
            "name": name,
            "gcp_user_id": gcp_user_id,
            "gcp_provider": "google",
            "password": None  # No password for Google users
        }
        mock_users[email] = user
    
    # Generate token
    token = generate_token()
    active_tokens[token] = user["id"]
    
    # Store auth credentials (mock - in production, store in database)
    # This would go to auth_credentials table in Cloud SQL
    credential_data = {
        "user_id": user["id"],
        "access_token": credential,  # In production, store actual access token
        "id_token": credential,
        "provider": "google",
        "provider_user_id": gcp_user_id,
        "provider_email": email,
        "expires_at": datetime.now() + timedelta(hours=1),  # Mock expiration
    }
    print(f"✅ Google auth successful for {email}")
    print(f"   GCP User ID: {gcp_user_id}")
    print(f"   User ID: {user['id']}")
    print(f"   Token generated: {token[:20]}...")
    print(f"   Auth credentials stored (mock): {json.dumps(credential_data, default=str)}")
    
    response_data = {
        "user": UserResponse(**{k: v for k, v in user.items() if k != "password"}),
        "token": token
    }
    
    print("=" * 60)
    print("✅ BACKEND: Returning response")
    print(f"   User: {response_data['user'].email}")
    print(f"   Token length: {len(response_data['token'])}")
    print("=" * 60)
    
    return response_data

# ============================================================================
# Chat Endpoints
# ============================================================================

@app.post("/api/chat/message", response_model=SendMessageResponse, status_code=200)
async def send_message(
    request: MessageRequest,
    current_user: dict = Depends(require_auth)
):
    """Send a message in a conversation"""
    conversation_id = request.conversationId
    
    # Create conversation if it doesn't exist
    if not conversation_id or conversation_id not in mock_conversations:
        # Create new conversation
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        title = request.message[:50] if request.message else "New Conversation"
        
        new_conv = ConversationResponse(
            id=conversation_id,
            title=title,
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            messageCount=0
        )
        mock_conversations[conversation_id] = new_conv
        mock_messages[conversation_id] = []
    
    # Create user message
    user_message = MessageResponse(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        role="user",
        content=request.message,
        timestamp=datetime.now(),
        conversationId=conversation_id
    )
    
    # Add user message
    if conversation_id not in mock_messages:
        mock_messages[conversation_id] = []
    mock_messages[conversation_id].append(user_message)
    
    # Generate assistant response (mock)
    assistant_responses = [
        f"Based on the financial data, {request.message.lower()} shows interesting patterns. Let me analyze this further.",
        f"I've analyzed the market data related to your question about '{request.message[:30]}...'. Here are my insights:\n\n1. Market indicators suggest moderate volatility\n2. Technical analysis shows potential upward trend\n3. Fundamental analysis indicates strong financial health",
        f"Great question! Regarding '{request.message[:40]}...', our multi-agent system has processed this and here's what we found:\n\n**Analysis Summary:**\n- Sentiment: Positive\n- Risk Level: Moderate\n- Recommendation: Consider further research\n\nWould you like me to dive deeper into any specific aspect?",
        f"Thank you for your question. I've consulted our financial analysis agents and here's what they found:\n\n```\nAnalysis Results:\n- Market Data: Processed\n- News Sentiment: Analyzed\n- Technical Indicators: Calculated\n```\n\nBased on this analysis, I recommend reviewing the detailed reports in your dashboard."
    ]
    
    assistant_message = MessageResponse(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        role="assistant",
        content=random.choice(assistant_responses),
        timestamp=datetime.now(),
        conversationId=conversation_id
    )
    
    # Add assistant message
    mock_messages[conversation_id].append(assistant_message)
    
    # Update conversation
    if conversation_id in mock_conversations:
        conv = mock_conversations[conversation_id]
        conv.messageCount = len(mock_messages[conversation_id])
        conv.updatedAt = datetime.now()
    
    return {
        "message": assistant_message,
        "conversationId": conversation_id
    }

@app.get("/api/chat/conversations", status_code=200)
async def get_conversations(current_user: dict = Depends(require_auth)):
    """Get all conversations for the current user"""
    # Return all conversations (in production, filter by user_id)
    conversations = list(mock_conversations.values())
    
    # Sort by updatedAt descending
    conversations.sort(key=lambda x: x.updatedAt, reverse=True)
    
    return {"conversations": conversations}

@app.post("/api/chat/conversations", response_model=CreateConversationResponse, status_code=200)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: dict = Depends(require_auth)
):
    """Create a new conversation"""
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
    title = request.title or f"New Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    new_conv = ConversationResponse(
        id=conversation_id,
        title=title,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
        messageCount=0
    )
    
    mock_conversations[conversation_id] = new_conv
    mock_messages[conversation_id] = []
    
    return {"conversation": new_conv}

@app.get("/api/chat/conversations/{conversation_id}/messages", status_code=200)
async def get_messages(
    conversation_id: str,
    current_user: dict = Depends(require_auth)
):
    """Get all messages for a conversation"""
    if conversation_id not in mock_conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = mock_messages.get(conversation_id, [])
    
    # Sort by timestamp ascending
    messages.sort(key=lambda x: x.timestamp)
    
    return {
        "messages": messages,
        "conversationId": conversation_id
    }

@app.delete("/api/chat/conversations/{conversation_id}", status_code=200)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_auth)
):
    """Delete a conversation"""
    if conversation_id not in mock_conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del mock_conversations[conversation_id]
    if conversation_id in mock_messages:
        del mock_messages[conversation_id]
    
    return {"message": "Conversation deleted successfully"}

# ============================================================================
# ============================================================================
# Agents Service Integration
# ============================================================================

class ConversationMessage(BaseModel):
    """Message in conversation context for agents analysis."""
    id: str = Field(..., description="Message ID (format: msg-{uuid})")
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp in ISO format (e.g., '2024-12-19T10:00:00Z')")
    metadata: Optional[dict] = Field(None, description="Optional message metadata")

class AgentAnalyzeRequest(BaseModel):
    """Request model for agents analysis endpoint."""
    company_name: str = Field(..., description="Company name or ticker symbol (e.g., 'AAPL', 'Apple Inc.')", min_length=1, max_length=100)
    trade_date: str = Field(..., description="Trade date in ISO format YYYY-MM-DD (e.g., '2024-12-19')", pattern=r'^\d{4}-\d{2}-\d{2}$')
    conversation_context: Optional[List[ConversationMessage]] = Field(None, description="Optional conversation context (chat history) to provide context to agents (max 50 messages, last 20 used)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "AAPL",
                "trade_date": "2024-12-19",
                "conversation_context": [
                    {
                        "id": "msg-12345678",
                        "role": "user",
                        "content": "What about Apple?",
                        "timestamp": "2024-12-19T10:00:00Z"
                    }
                ]
            }
        }

class AgentAnalyzeResponse(BaseModel):
    """Response model for agents analysis endpoint."""
    company: str = Field(..., description="Company name or ticker")
    date: str = Field(..., description="Trade date")
    decision: str = Field(..., description="Trading decision: 'BUY', 'SELL', or 'HOLD'")
    state: dict = Field(..., description="Complete analysis state with all agent outputs and reports")

@app.post("/api/agents/analyze", response_model=AgentAnalyzeResponse)
async def agents_analyze(request: AgentAnalyzeRequest):
    """
    Analyze a company using the agents service.
    Proxies request to agents service at AGENTS_SERVICE_URL/analyze
    
    Supports optional conversation_context for providing chat history to agents.
    """
    import httpx
    
    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    analyze_endpoint = f"{agents_url}/analyze"
    
    # Build request payload
    payload = {
        "company_name": request.company_name,
        "trade_date": request.trade_date
    }
    
    # Add conversation context if provided
    if request.conversation_context:
        payload["conversation_context"] = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata
            }
            for msg in request.conversation_context
        ]
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout for analysis
            response = await client.post(
                analyze_endpoint,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors with status codes
        error_detail = f"Agents service error: {e.response.status_code}"
        try:
            error_body = e.response.json()
            if "detail" in error_body:
                error_detail = f"Agents service error: {error_body['detail']}"
        except:
            error_detail = f"Agents service error: {e.response.text or str(e)}"
        
        raise HTTPException(
            status_code=e.response.status_code if e.response.status_code < 500 else 502,
            detail=error_detail
        )
    except httpx.RequestError as e:
        # Handle connection errors, timeouts, etc.
        raise HTTPException(
            status_code=503,
            detail=f"Agents service unavailable: {str(e)}"
        )

# Agents Health Check (Proxy to Agents Service)
# ============================================================================

@app.get("/api/agents/health")
async def agents_health():
    """
    Agents health check endpoint.
    Returns status for agent backend.
    Uses AGENTS_SERVICE_URL environment variable (default: http://localhost:8001)
    For Docker, set AGENTS_SERVICE_URL=http://meridian-agents:8001
    """
    import httpx
    
    # Get agents service URL from environment, default to localhost for local dev
    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    health_endpoint = f"{agents_url}/health"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_endpoint)
            response.raise_for_status()
            data = response.json()
            return {
                "status": "ok", 
                "agent_service": data,
                "agents_url": agents_url
            }
    except httpx.ConnectError as e:
        return {
            "status": "error",
            "message": f"Connection error: Could not reach agent service at {health_endpoint}",
            "error": str(e),
            "agents_url": agents_url
        }
    except httpx.TimeoutException as e:
        return {
            "status": "error",
            "message": f"Timeout: Agent service did not respond within 5 seconds",
            "error": str(e),
            "agents_url": agents_url
        }
    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "message": f"HTTP error: Agent service returned {e.response.status_code}",
            "error": str(e),
            "agents_url": agents_url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
            "agents_url": health_endpoint
        }

# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
