# Meridian Agents Service API Reference

## Overview

The Meridian Agents Service is a FastAPI microservice that orchestrates financial analysis agents using OpenAI Agents SDK and LangGraph. This document provides comprehensive API documentation.

**Base URL**: `http://localhost:8001` (default)  
**Service Name**: `meridian-agents`  
**Version**: 1.0.0

---

## Authentication

Currently, the agents service does not require authentication. Future versions may implement API key authentication.

---

## Endpoints

### Health Check

**Endpoint**: `GET /health`

**Description**: Returns service health status and graph initialization state. Always returns HTTP 200, even if graph initialization fails.

**Response Model**: `HealthResponse`

**Response Fields**:
- `status` (string): Service status - `"ok"` or `"error"`
- `service` (string): Service name - `"meridian-agents"`
- `graph_initialized` (boolean): Whether the TradingAgentsGraph is initialized
- `error` (string, optional): Error message if status is `"error"`

**Example Request**:
```bash
curl http://localhost:8001/health
```

**Example Response (Success)**:
```json
{
  "status": "ok",
  "service": "meridian-agents",
  "graph_initialized": true
}
```

**Example Response (Error)**:
```json
{
  "status": "error",
  "service": "meridian-agents",
  "graph_initialized": false,
  "error": "Failed to initialize TradingAgentsGraph: ..."
}
```

**Response Time**: < 5 seconds (constitution requirement)

---

### Analyze Company

**Endpoint**: `POST /analyze`

**Description**: Analyzes a company using the agents service. Runs the complete agent workflow and returns trading decision and analysis state.

**Request Model**: `AnalyzeRequest`

**Request Fields**:
- `company_name` (string, required): Company name or ticker symbol (e.g., "AAPL", "Apple Inc.")
- `trade_date` (string, required): Trade date in ISO format `YYYY-MM-DD` (e.g., "2024-12-19")
- `conversation_context` (array, optional): Array of conversation messages for context (max 50, last 20 used)

**Conversation Message Format**:
```json
{
  "id": "msg-12345678",
  "role": "user" | "assistant" | "system",
  "content": "Message content",
  "timestamp": "2024-12-19T10:00:00Z",
  "metadata": {} // optional
}
```

**Response Model**: `AnalyzeResponse`

**Response Fields**:
- `company` (string): Company name or ticker
- `date` (string): Trade date
- `decision` (string): Trading decision - `"BUY"`, `"SELL"`, or `"HOLD"`
- `state` (object): Complete graph state with all agent outputs

**Example Request**:
```bash
curl -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "AAPL",
    "trade_date": "2024-12-19"
  }'
```

**Example Request with Context**:
```bash
curl -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

**Example Response**:
```json
{
  "company": "AAPL",
  "date": "2024-12-19",
  "decision": "BUY",
  "state": {
    "market_report": "...",
    "fundamentals_report": "...",
    "information_report": "...",
    "bull_research": "...",
    "bear_research": "...",
    "research_summary": "...",
    "trading_decision": "BUY"
  }
}
```

**Timeout**: 300 seconds (5 minutes)

**Error Responses**:
- `400`: Validation error (invalid input)
- `422`: Pydantic validation error (malformed request)
- `500`: Internal server error (analysis failed)

---

## Error Responses

All error responses follow this format:

**Development Mode**:
```json
{
  "detail": "Error message with full traceback",
  "error_type": "ExceptionClassName",
  "traceback": "Full stack trace..."
}
```

**Production Mode**:
```json
{
  "detail": "Sanitized error message",
  "error_type": "ExceptionClassName"
}
```

---

## Request/Response Models

### AnalyzeRequest

```python
{
  "company_name": str,  # Required, 1-100 chars
  "trade_date": str,     # Required, format: YYYY-MM-DD
  "conversation_context": [  # Optional, max 50 items
    {
      "id": str,
      "role": str,  # "user" | "assistant" | "system"
      "content": str,
      "timestamp": str,  # ISO format
      "metadata": {}  # Optional
    }
  ]
}
```

### HealthResponse

```python
{
  "status": str,           # "ok" | "error"
  "service": str,          # "meridian-agents"
  "graph_initialized": bool,
  "error": str | None      # Optional error message
}
```

### AnalyzeResponse

```python
{
  "company": str,
  "date": str,
  "decision": str,         # "BUY" | "SELL" | "HOLD"
  "state": {               # Complete graph state
    # Agent outputs and analysis results
  }
}
```

---

## Environment Variables

### Required

- `OPENAI_API_KEY`: OpenAI API key for agent execution

### Optional

- `PORT`: Service port (default: `8001`)
- `LOG_LEVEL`: Logging level - `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default: `INFO`)
- `ENVIRONMENT`: Deployment environment - `development`, `production`, `testing` (default: `development`)
- `LOG_FILE`: Path to log file (optional)

---

## Integration with Backend

The backend service calls the agents service via HTTP:

**Backend Configuration**:
```python
AGENTS_SERVICE_URL=http://localhost:8001  # Local development
AGENTS_SERVICE_URL=http://meridian-agents:8001  # Docker deployment
```

**Backend Endpoint**: `POST /api/agents/analyze`

The backend proxies requests to the agents service and handles:
- User authentication
- Conversation management
- Message storage
- Response formatting

---

## Logging

The service uses structured JSON logging with the following fields:

```json
{
  "timestamp": "2024-12-19T10:00:00Z",
  "level": "INFO",
  "logger": "meridian_agents",
  "message": "Analysis requested",
  "module": "server",
  "function": "analyze",
  "line": 213,
  "request_id": "req-1234567890",
  "endpoint": "/analyze",
  "company": "AAPL",
  "trade_date": "2024-12-19"
}
```

**Log Levels**:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical error messages

---

## Performance

- **Health Check**: < 5 seconds response time
- **Analysis**: Up to 300 seconds (5 minutes) for complex analyses
- **Concurrent Requests**: Thread-safe, supports multiple simultaneous requests

---

## Testing

Run tests with:
```bash
cd meridian-agents
python3 -m pytest tests/ -v
```

Test coverage target: > 70%

---

## Docker Deployment

**Build**:
```bash
docker build -f Dockerfile.agents -t meridian-agents:latest .
```

**Run**:
```bash
docker run -d \
  -p 8001:8001 \
  --name meridian-agents \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  meridian-agents:latest
```

**Health Check**:
```bash
curl http://localhost:8001/health
```

---

## Constitution Compliance

This service adheres to the Meridian Agents Service Constitution (v2.0.0):

- ✅ Service-oriented architecture (independent microservice)
- ✅ OpenAI Agents SDK integration
- ✅ Lazy graph initialization (thread-safe)
- ✅ Standardized API models (Pydantic)
- ✅ Health check endpoint (always returns 200)
- ✅ Analysis endpoint contract
- ✅ Backend service integration (HTTP/REST)
- ✅ Error handling and logging
- ✅ Naming conventions
- ✅ Testing and testability

---

**Last Updated**: 2024-12-19  
**API Version**: 1.0.0

