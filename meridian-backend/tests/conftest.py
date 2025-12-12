"""
Pytest configuration and fixtures for Meridian Backend tests.
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dotenv import load_dotenv

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Load environment variables from .env file
# Try to find .env file in project root (parent of meridian-backend)
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=False)  # Don't override existing env vars
elif (Path(__file__).parent.parent / ".env").exists():
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
else:
    # Try current directory
    load_dotenv(override=False)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import server app
try:
    from server import app
except ImportError as e:
    # If import fails, create a minimal app for testing
    from fastapi import FastAPI
    app = FastAPI(title="Meridian Backend API Test")
    print(f"Warning: Could not import full server, using minimal app: {e}")
except Exception as e:
    # Catch any other errors during import
    from fastapi import FastAPI
    app = FastAPI(title="Meridian Backend API Test")
    print(f"Warning: Error importing server, using minimal app: {e}")


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_config(monkeypatch, request):
    """Mock configuration for testing (auto-use for all tests)."""
    # Set test environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("PORT", "8000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("AGENTS_SERVICE_URL", "http://localhost:8001")
    
    # Check if test requires real database - if so, don't override DB env vars
    # This allows integration tests to use real credentials from .env file
    requires_db = any(marker.name == "requires_db" for marker in request.node.iter_markers())
    requires_gcp = any(marker.name == "requires_gcp" for marker in request.node.iter_markers())
    
    if not (requires_db or requires_gcp):
        # Database config (only set for non-integration tests)
        monkeypatch.setenv("DB_HOST", "test-host")
        monkeypatch.setenv("DB_USER", "test-user")
        monkeypatch.setenv("DB_PASSWORD", "test-password")
        monkeypatch.setenv("DB_NAME", "test-db")
        monkeypatch.setenv("DB_TYPE", "postgresql")
    
    # Reload config if available
    try:
        from utils.config import get_config
        import utils.config as config_module
        if hasattr(config_module, '_config'):
            config_module._config = None
        return get_config()
    except ImportError:
        # If import fails, just set env vars
        pass


@pytest.fixture
def mock_db_client():
    """Mock database client for testing."""
    mock_client = MagicMock()
    mock_conn = AsyncMock()
    
    # Mock connection context manager
    async def mock_get_connection():
        return mock_conn
    
    mock_client.get_connection = AsyncMock(return_value=mock_conn)
    mock_client.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_client.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
    
    return mock_client


@pytest.fixture
def mock_query_classifier():
    """Mock query classifier for testing."""
    mock_classifier = MagicMock()
    return mock_classifier


@pytest.fixture
def mock_agent_orchestrator():
    """Mock agent orchestrator for testing."""
    mock_orchestrator = MagicMock()
    
    # Mock classify_and_get_workflow (synchronous method)
    def mock_classify_and_get_workflow(query: str, conversation_context=None):
        from models.query_intent import QueryIntent
        from models.agent_workflow import AgentWorkflowConfig
        
        # Return a default workflow
        workflow = AgentWorkflowConfig(
            workflow_type="simple_chat",
            agents=[],
            timeout_seconds=30
        )
        return QueryIntent.SIMPLE_CHAT, workflow
    
    mock_orchestrator.classify_and_get_workflow = MagicMock(side_effect=mock_classify_and_get_workflow)
    return mock_orchestrator


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service for testing."""
    mock_service = MagicMock()
    
    async def mock_chat_completion(*args, **kwargs):
        return {
            "id": "test-completion-id",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                }
            }]
        }
    
    mock_service.chat_completion = AsyncMock(side_effect=mock_chat_completion)
    return mock_service


@pytest.fixture
def sample_thread_data():
    """Sample thread data for testing."""
    return {
        "thread_id": "test-thread-123",
        "title": "Test Thread",
        "user_id": "test-user-123",
        "created_at": "2024-12-19T10:00:00Z",
        "updated_at": "2024-12-19T10:00:00Z"
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "message_id": "test-msg-123",
        "thread_id": "test-thread-123",
        "role": "user",
        "content": "Test message",
        "timestamp": "2024-12-19T10:00:00Z"
    }


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return {
        "thread_id": "test-thread-123",
        "message": "What is Apple stock trading at?",
        "query": None
    }

