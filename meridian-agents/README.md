# Meridian Agents Service

FastAPI microservice for orchestrating financial analysis agents using OpenAI Agents SDK and LangGraph.

## Features

- **Multi-Agent Analysis**: Orchestrates specialized agents for market, fundamentals, and information analysis
- **Thread-Safe**: Concurrent request handling with thread-safe graph initialization
- **Structured Logging**: JSON-formatted logs with request tracking
- **Error Handling**: Comprehensive error handling with production-safe responses
- **Conversation Context**: Supports conversation history for context-aware analysis
- **Constitution Compliant**: Adheres to Meridian Agents Service Constitution v2.0.0

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- All dependencies from `requirements.txt`

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your-api-key
export PORT=8001  # Optional, defaults to 8001
export LOG_LEVEL=INFO  # Optional, defaults to INFO
export ENVIRONMENT=development  # Optional, defaults to development
```

### Running the Service

```bash
# Direct execution
python meridian-agents/server.py

# Or with uvicorn
uvicorn server:app --host 0.0.0.0 --port 8001
```

### Docker

```bash
# Build
docker build -f Dockerfile.agents -t meridian-agents:latest .

# Run
docker run -d \
  -p 8001:8001 \
  --name meridian-agents \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  meridian-agents:latest
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service status and graph initialization state.

### Analyze

```bash
POST /analyze
Content-Type: application/json

{
  "company_name": "AAPL",
  "trade_date": "2024-12-19",
  "conversation_context": []  // Optional
}
```

Runs complete agent workflow and returns trading decision.

See [API Reference](docs/agents_api_reference.md) for detailed documentation.

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=server --cov=models --cov=utils --cov-report=html

# Run specific test file
python3 -m pytest tests/test_health.py -v
```

**Test Coverage Target**: > 70%

## Project Structure

```
meridian-agents/
├── server.py              # FastAPI application
├── models/                # Pydantic models
│   ├── requests.py
│   └── responses.py
├── utils/                 # Utilities
│   ├── config.py          # Configuration
│   ├── logging.py         # Structured logging
│   └── errors.py          # Error handling
├── tests/                 # Tests
│   ├── test_health.py
│   ├── test_analyze.py
│   ├── test_logging.py
│   ├── test_errors.py
│   └── integration/
├── agents_module/         # Agent implementations
├── graph/                 # LangGraph orchestration
└── dataflows/            # Data source integrations
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `PORT` | No | `8001` | Service port |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `ENVIRONMENT` | No | `development` | Deployment environment |
| `LOG_FILE` | No | - | Log file path (optional) |

## Logging

The service uses structured JSON logging:

```json
{
  "timestamp": "2024-12-19T10:00:00Z",
  "level": "INFO",
  "message": "Analysis requested",
  "request_id": "req-1234567890",
  "endpoint": "/analyze",
  "company": "AAPL"
}
```

## Integration

### Backend Integration

The backend service calls the agents service:

```python
import httpx

agents_url = os.getenv("AGENTS_SERVICE_URL", "http://localhost:8001")
response = await httpx.post(
    f"{agents_url}/analyze",
    json={
        "company_name": "AAPL",
        "trade_date": "2024-12-19"
    },
    timeout=300.0
)
```

**Backend Configuration**:
- `AGENTS_SERVICE_URL=http://localhost:8001` (local)
- `AGENTS_SERVICE_URL=http://meridian-agents:8001` (Docker)

## Constitution Compliance

This service adheres to the [Meridian Agents Service Constitution](.specify/memory/constitution.md):

- ✅ Service-oriented architecture
- ✅ OpenAI Agents SDK integration
- ✅ Thread-safe graph initialization
- ✅ Standardized API models
- ✅ Health check endpoint
- ✅ Error handling and logging
- ✅ Testing and testability

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_health.py -v

# With coverage
pytest tests/ --cov --cov-report=html
```

### Code Quality

- Type hints required
- Pydantic models for validation
- Structured logging
- Error handling with proper HTTP status codes

## Documentation

- [API Reference](docs/agents_api_reference.md)
- [Constitution](.specify/memory/constitution.md)
- [Chat Session Management](docs/chat_session_management.md)

## License

[Add license information]

---

**Version**: 1.0.0  
**Last Updated**: 2024-12-19

