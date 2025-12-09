# Chat Session Management Guidelines

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Naming Conventions](#naming-conventions)
4. [Data Models](#data-models)
5. [Session Lifecycle](#session-lifecycle)
6. [Conversation History](#conversation-history)
7. [API Endpoints](#api-endpoints)
8. [Database Schema](#database-schema)
9. [Best Practices](#best-practices)
10. [Implementation Examples](#implementation-examples)

---

## Overview

This document provides comprehensive guidelines for managing chat sessions, conversation history, and related data structures in the Meridian backend system.

### Key Concepts

- **Session**: A user's active connection to the chat service
- **Conversation**: A collection of messages between a user and the assistant
- **Message**: A single exchange (user or assistant) within a conversation
- **Context**: The conversation history and metadata used for agent analysis

---

## Architecture

### Service Layers

```
┌─────────────────┐
│   Frontend      │
│  (Next.js)      │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│   Backend API   │
│  (FastAPI)      │
│  - Auth         │
│  - Chat Mgmt    │
│  - Sessions     │
└────────┬────────┘
         │
         ├──────────────┐
         ▼              ▼
┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │  Agents Service │
│   Database      │  │  (FastAPI)      │
│  - Conversations│  │  - Analysis     │
│  - Messages     │  │  - Graph       │
│  - Sessions     │  └─────────────────┘
└─────────────────┘
```

### Data Flow

1. **User sends message** → Frontend → Backend API
2. **Backend creates/updates conversation** → Database
3. **Backend calls agents service** → Analysis
4. **Backend stores response** → Database
5. **Backend returns response** → Frontend

---

## Naming Conventions

### Identifiers

| Type | Format | Example | Notes |
|------|--------|---------|-------|
| **Conversation ID** | `conv-{uuid}` | `conv-a1b2c3d4` | Lowercase, hyphenated |
| **Message ID** | `msg-{uuid}` | `msg-e5f6g7h8` | Lowercase, hyphenated |
| **Session ID** | `sess-{uuid}` | `sess-i9j0k1l2` | Lowercase, hyphenated |
| **User ID** | `user-{uuid}` | `user-m3n4o5p6` | Lowercase, hyphenated |

### Database Tables

| Table | Naming | Example |
|-------|--------|---------|
| **Conversations** | `conversations` | `meridian.conversations` |
| **Messages** | `messages` | `meridian.messages` |
| **Sessions** | `chat_sessions` | `meridian.chat_sessions` |

### API Endpoints

| Endpoint | Method | Pattern |
|----------|--------|---------|
| **List conversations** | `GET` | `/api/chat/conversations` |
| **Create conversation** | `POST` | `/api/chat/conversations` |
| **Get conversation** | `GET` | `/api/chat/conversations/{id}` |
| **Update conversation** | `PATCH` | `/api/chat/conversations/{id}` |
| **Delete conversation** | `DELETE` | `/api/chat/conversations/{id}` |
| **Get messages** | `GET` | `/api/chat/conversations/{id}/messages` |
| **Send message** | `POST` | `/api/chat/message` |
| **Stream message** | `POST` | `/api/chat/message/stream` |

### Variables and Functions

```python
# Python (Backend)
conversation_id: str  # snake_case
conversation_title: str
message_content: str
user_id: str

# TypeScript (Frontend)
conversationId: string  # camelCase
conversationTitle: string
messageContent: string
userId: string
```

---

## Data Models

### Conversation Model

```python
class Conversation(BaseModel):
    id: str                    # Format: "conv-{uuid}"
    user_id: str              # Format: "user-{uuid}"
    title: str                # Auto-generated or user-provided
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime]
    message_count: int
    is_archived: bool = False
    is_pinned: bool = False
    metadata: Optional[dict] = {}  # Custom metadata
```

### Message Model

```python
class Message(BaseModel):
    id: str                    # Format: "msg-{uuid}"
    conversation_id: str       # Format: "conv-{uuid}"
    role: MessageRole          # "user" | "assistant" | "system"
    content: str
    timestamp: datetime
    metadata: Optional[dict] = {}  # Agent analysis, tokens, etc.
    parent_message_id: Optional[str] = None  # For threading
```

### Session Model

```python
class ChatSession(BaseModel):
    id: str                    # Format: "sess-{uuid}"
    user_id: str              # Format: "user-{uuid}"
    conversation_id: Optional[str]  # Active conversation
    created_at: datetime
    last_activity_at: datetime
    expires_at: Optional[datetime]
    metadata: Optional[dict] = {}
```

---

## Session Lifecycle

### 1. Session Creation

**Trigger**: User authenticates and opens chat interface

```python
# Backend: Create session on first message or explicit request
async def create_session(user_id: str) -> ChatSession:
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    session = ChatSession(
        id=session_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    # Store in database or cache
    return session
```

### 2. Conversation Creation

**Trigger**: User sends first message or explicitly creates conversation

```python
# Auto-create conversation on first message
async def send_message(user_id: str, content: str, conversation_id: Optional[str] = None):
    if not conversation_id:
        # Create new conversation
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        title = generate_title(content)  # Auto-generate from first message
        conversation = await create_conversation(user_id, conversation_id, title)
    
    # Create and store message
    message = await create_message(conversation_id, "user", content)
    
    # Process with agents
    response = await process_with_agents(conversation_id, content)
    
    # Store assistant response
    assistant_message = await create_message(conversation_id, "assistant", response)
    
    return {"conversationId": conversation_id, "message": assistant_message}
```

### 3. Title Generation

**Strategy**: Generate from first user message

```python
def generate_title(message: str, max_length: int = 50) -> str:
    """Generate conversation title from first message"""
    # Remove markdown, URLs, special chars
    cleaned = re.sub(r'[#*_`]', '', message)
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    
    # Take first sentence or first 50 chars
    title = cleaned.split('.')[0].strip()
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    
    # Fallback
    if not title:
        title = f"New Conversation {datetime.now().strftime('%Y-%m-%d')}"
    
    return title
```

### 4. Session Expiration

**Strategy**: Inactive sessions expire after 24 hours

```python
async def cleanup_expired_sessions():
    """Remove expired sessions"""
    expired = await db.query(
        "SELECT id FROM chat_sessions WHERE expires_at < NOW()"
    )
    for session in expired:
        await db.delete("chat_sessions", session.id)
```

---

## Conversation History

### Message Ordering

**Rule**: Always order by `timestamp ASC` for chronological display

```python
async def get_messages(conversation_id: str) -> List[Message]:
    messages = await db.query(
        """
        SELECT * FROM messages 
        WHERE conversation_id = $1 
        ORDER BY timestamp ASC
        """,
        conversation_id
    )
    return messages
```

### Pagination

**Strategy**: Use cursor-based pagination for large conversations

```python
class MessagePagination(BaseModel):
    limit: int = 50
    cursor: Optional[str] = None  # Message ID

async def get_messages_paginated(
    conversation_id: str,
    pagination: MessagePagination
) -> List[Message]:
    query = """
        SELECT * FROM messages 
        WHERE conversation_id = $1
    """
    params = [conversation_id]
    
    if pagination.cursor:
        query += " AND timestamp > (SELECT timestamp FROM messages WHERE id = $2)"
        params.append(pagination.cursor)
    
    query += " ORDER BY timestamp ASC LIMIT $2"
    params.append(pagination.limit)
    
    return await db.query(query, *params)
```

### Context Window Management

**Strategy**: Limit context sent to agents (last N messages)

```python
MAX_CONTEXT_MESSAGES = 20  # Last 20 messages for agent context

async def get_context_for_agents(conversation_id: str) -> List[Message]:
    """Get recent messages for agent context"""
    messages = await db.query(
        """
        SELECT * FROM messages 
        WHERE conversation_id = $1 
        ORDER BY timestamp DESC 
        LIMIT $2
        """,
        conversation_id,
        MAX_CONTEXT_MESSAGES
    )
    return list(reversed(messages))  # Return in chronological order
```

---

## API Endpoints

### 1. List Conversations

```python
@app.get("/api/chat/conversations")
async def get_conversations(
    current_user: dict = Depends(require_auth),
    limit: int = 50,
    offset: int = 0,
    archived: bool = False
):
    """Get all conversations for current user"""
    conversations = await db.query(
        """
        SELECT * FROM conversations 
        WHERE user_id = $1 AND is_archived = $2
        ORDER BY updated_at DESC
        LIMIT $3 OFFSET $4
        """,
        current_user["id"],
        archived,
        limit,
        offset
    )
    return {"conversations": conversations}
```

### 2. Create Conversation

```python
@app.post("/api/chat/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: dict = Depends(require_auth)
):
    """Create a new conversation"""
    conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
    title = request.title or f"New Conversation {datetime.now().strftime('%Y-%m-%d')}"
    
    conversation = await db.insert(
        "conversations",
        {
            "id": conversation_id,
            "user_id": current_user["id"],
            "title": title,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "message_count": 0
        }
    )
    return {"conversation": conversation}
```

### 3. Send Message

```python
@app.post("/api/chat/message")
async def send_message(
    request: MessageRequest,
    current_user: dict = Depends(require_auth)
):
    """Send a message in a conversation"""
    conversation_id = request.conversationId
    
    # Auto-create conversation if needed
    if not conversation_id:
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        title = generate_title(request.message)
        await create_conversation(current_user["id"], conversation_id, title)
    
    # Create user message
    user_message = await db.insert(
        "messages",
        {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow()
        }
    )
    
    # Process with agents
    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{agents_url}/analyze",
            json={
                "company_name": extract_company(request.message),  # Extract from message
                "trade_date": datetime.now().isoformat(),
                "conversation_context": await get_context_for_agents(conversation_id)
            }
        )
        analysis = response.json()
    
    # Create assistant message
    assistant_message = await db.insert(
        "messages",
        {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": analysis["decision"],
            "timestamp": datetime.utcnow(),
            "metadata": {"analysis": analysis}
        }
    )
    
    # Update conversation
    await db.update(
        "conversations",
        conversation_id,
        {
            "updated_at": datetime.utcnow(),
            "last_message_at": datetime.utcnow(),
            "message_count": await db.count("messages", {"conversation_id": conversation_id})
        }
    )
    
    return {
        "message": assistant_message,
        "conversationId": conversation_id
    }
```

### 4. Get Messages

```python
@app.get("/api/chat/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    current_user: dict = Depends(require_auth),
    limit: int = 50,
    cursor: Optional[str] = None
):
    """Get messages for a conversation"""
    # Verify ownership
    conversation = await db.get("conversations", conversation_id)
    if not conversation or conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await get_messages_paginated(conversation_id, limit, cursor)
    return {"messages": messages, "conversationId": conversation_id}
```

### 5. Update Conversation

```python
@app.patch("/api/chat/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: dict = Depends(require_auth)
):
    """Update conversation (title, archive, pin)"""
    # Verify ownership
    conversation = await db.get("conversations", conversation_id)
    if not conversation or conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    updates = {}
    if request.title:
        updates["title"] = request.title
    if request.is_archived is not None:
        updates["is_archived"] = request.is_archived
    if request.is_pinned is not None:
        updates["is_pinned"] = request.is_pinned
    
    updates["updated_at"] = datetime.utcnow()
    
    conversation = await db.update("conversations", conversation_id, updates)
    return {"conversation": conversation}
```

### 6. Delete Conversation

```python
@app.delete("/api/chat/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_auth)
):
    """Delete a conversation and all its messages"""
    # Verify ownership
    conversation = await db.get("conversations", conversation_id)
    if not conversation or conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Soft delete: mark as archived and hide from list
    await db.update(
        "conversations",
        conversation_id,
        {"is_archived": True, "deleted_at": datetime.utcnow()}
    )
    
    # Or hard delete (if required):
    # await db.delete("messages", {"conversation_id": conversation_id})
    # await db.delete("conversations", conversation_id)
    
    return {"message": "Conversation deleted successfully"}
```

---

## Database Schema

### Conversations Table

```sql
CREATE TABLE meridian.conversations (
    id VARCHAR(50) PRIMARY KEY,  -- Format: "conv-{uuid}"
    user_id VARCHAR(50) NOT NULL,  -- Format: "user-{uuid}"
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE,
    message_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    is_pinned BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT fk_conversations_user 
        FOREIGN KEY (user_id) 
        REFERENCES meridian.users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_conversations_user ON meridian.conversations(user_id);
CREATE INDEX idx_conversations_updated ON meridian.conversations(updated_at DESC);
CREATE INDEX idx_conversations_archived ON meridian.conversations(is_archived);
CREATE INDEX idx_conversations_pinned ON meridian.conversations(is_pinned);
```

### Messages Table

```sql
CREATE TABLE meridian.messages (
    id VARCHAR(50) PRIMARY KEY,  -- Format: "msg-{uuid}"
    conversation_id VARCHAR(50) NOT NULL,  -- Format: "conv-{uuid}"
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    parent_message_id VARCHAR(50),
    
    CONSTRAINT fk_messages_conversation 
        FOREIGN KEY (conversation_id) 
        REFERENCES meridian.conversations(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_messages_parent 
        FOREIGN KEY (parent_message_id) 
        REFERENCES meridian.messages(id)
        ON DELETE SET NULL
);

CREATE INDEX idx_messages_conversation ON meridian.messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON meridian.messages(timestamp ASC);
CREATE INDEX idx_messages_role ON meridian.messages(role);
```

### Chat Sessions Table (Optional)

```sql
CREATE TABLE meridian.chat_sessions (
    id VARCHAR(50) PRIMARY KEY,  -- Format: "sess-{uuid}"
    user_id VARCHAR(50) NOT NULL,
    conversation_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT fk_sessions_user 
        FOREIGN KEY (user_id) 
        REFERENCES meridian.users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_sessions_conversation 
        FOREIGN KEY (conversation_id) 
        REFERENCES meridian.conversations(id)
        ON DELETE SET NULL
);

CREATE INDEX idx_sessions_user ON meridian.chat_sessions(user_id);
CREATE INDEX idx_sessions_expires ON meridian.chat_sessions(expires_at);
```

---

## Best Practices

### 1. Security

- **Always verify ownership**: Check `user_id` before allowing access
- **Use parameterized queries**: Prevent SQL injection
- **Validate input**: Sanitize message content
- **Rate limiting**: Limit messages per user per minute
- **Token expiration**: Expire sessions after inactivity

### 2. Performance

- **Index frequently queried columns**: `user_id`, `conversation_id`, `timestamp`
- **Paginate large result sets**: Use cursor-based pagination
- **Cache recent conversations**: Use Redis for active sessions
- **Batch operations**: Update `message_count` in batches
- **Async operations**: Use async/await for I/O operations

### 3. Data Integrity

- **Foreign key constraints**: Ensure referential integrity
- **Cascade deletes**: Delete messages when conversation is deleted
- **Transaction management**: Use transactions for multi-step operations
- **Unique constraints**: Prevent duplicate conversations

### 4. Error Handling

```python
# Always handle errors gracefully
try:
    conversation = await db.get("conversations", conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### 5. Logging

```python
# Log important operations
logger.info(f"Created conversation {conversation_id} for user {user_id}")
logger.info(f"Sent message in conversation {conversation_id}")
logger.warning(f"Attempted access to conversation {conversation_id} by unauthorized user")
```

---

## Implementation Examples

### Complete Message Flow

```python
async def handle_message_flow(
    user_id: str,
    message_content: str,
    conversation_id: Optional[str] = None
) -> dict:
    """Complete flow for handling a user message"""
    
    # 1. Get or create conversation
    if not conversation_id:
        conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        title = generate_title(message_content)
        await create_conversation(user_id, conversation_id, title)
    
    # 2. Store user message
    user_message_id = f"msg-{uuid.uuid4().hex[:8]}"
    await db.insert("messages", {
        "id": user_message_id,
        "conversation_id": conversation_id,
        "role": "user",
        "content": message_content,
        "timestamp": datetime.utcnow()
    })
    
    # 3. Get context for agents
    context = await get_context_for_agents(conversation_id)
    
    # 4. Call agents service
    agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{agents_url}/analyze",
            json={
                "company_name": extract_company(message_content),
                "trade_date": datetime.now().isoformat(),
                "conversation_context": [msg.dict() for msg in context]
            }
        )
        analysis = response.json()
    
    # 5. Store assistant response
    assistant_message_id = f"msg-{uuid.uuid4().hex[:8]}"
    await db.insert("messages", {
        "id": assistant_message_id,
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": analysis["decision"],
        "timestamp": datetime.utcnow(),
        "metadata": {"analysis": analysis}
    })
    
    # 6. Update conversation
    await db.update("conversations", conversation_id, {
        "updated_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "message_count": await db.count("messages", {"conversation_id": conversation_id})
    })
    
    return {
        "conversationId": conversation_id,
        "message": {
            "id": assistant_message_id,
            "role": "assistant",
            "content": analysis["decision"],
            "timestamp": datetime.utcnow()
        }
    }
```

### Title Generation

```python
import re
from datetime import datetime

def generate_title(message: str, max_length: int = 50) -> str:
    """Generate conversation title from message"""
    # Remove markdown
    cleaned = re.sub(r'[#*_`]', '', message)
    # Remove URLs
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    # Remove extra whitespace
    cleaned = ' '.join(cleaned.split())
    
    # Take first sentence or first N chars
    title = cleaned.split('.')[0].strip()
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    
    # Fallback
    if not title or len(title) < 3:
        title = f"New Conversation {datetime.now().strftime('%Y-%m-%d')}"
    
    return title
```

### Context Extraction

```python
def extract_company(message: str) -> Optional[str]:
    """Extract company name/ticker from message"""
    # Simple pattern matching (can be enhanced with NLP)
    patterns = [
        r'\b([A-Z]{2,5})\b',  # Ticker symbols (AAPL, MSFT)
        r'(\w+(?:\s+\w+)*)\s+(?:stock|shares|equity)',  # "Apple stock"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None
```

---

## Summary

### Key Takeaways

1. **Naming**: Use consistent prefixes (`conv-`, `msg-`, `sess-`) with UUIDs
2. **Lifecycle**: Auto-create conversations on first message
3. **History**: Order messages chronologically, paginate for large conversations
4. **Context**: Limit context window for agents (last 20 messages)
5. **Security**: Always verify user ownership before operations
6. **Performance**: Index frequently queried columns, use pagination
7. **Schema**: Use foreign keys, cascade deletes, JSONB for metadata

### Next Steps

1. Implement database schema in PostgreSQL
2. Update backend endpoints to use database instead of mock storage
3. Add Redis caching for active sessions
4. Implement streaming responses for real-time updates
5. Add conversation search and filtering

---

**Last Updated**: 2024-12-19  
**Version**: 1.0.0

