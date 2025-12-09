"""
Pytest configuration and fixtures for Meridian Agents Service tests.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock dependencies before importing server
sys.modules['graph'] = MagicMock()
sys.modules['graph.trading_graph'] = MagicMock()
sys.modules['agents_module'] = MagicMock()

# Import server app (adjust import path based on actual structure)
try:
    from server import app
except ImportError as e:
    # If import fails, create a minimal app for testing
    from fastapi import FastAPI
    app = FastAPI(title="Meridian Agents API Test")
    print(f"Warning: Could not import full server, using minimal app: {e}")


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    """Mock configuration for testing (auto-use for all tests)."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("PORT", "8001")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    
    # Reload config
    try:
        from utils.config import get_config
        import utils.config as config_module
        config_module._config = None
        return get_config()
    except ImportError:
        # If import fails, just set env vars
        pass


@pytest.fixture
def mock_graph():
    """Mock TradingAgentsGraph for testing."""
    mock = Mock()
    mock.propagate.return_value = (
        {"test": "state"},
        "BUY"
    )
    return mock


@pytest.fixture
def sample_analyze_request():
    """Sample analyze request data."""
    return {
        "company_name": "AAPL",
        "trade_date": "2024-12-19"
    }


@pytest.fixture
def sample_analyze_request_with_context():
    """Sample analyze request with conversation context."""
    return {
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

