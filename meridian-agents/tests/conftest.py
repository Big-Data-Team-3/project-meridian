"""
Pytest configuration and fixtures for Meridian Agents Service tests.
"""
import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock dependencies before importing server
# Create proper mock structure for nested imports
graph_mock = MagicMock()
graph_trading_graph_mock = MagicMock()
graph_planner_mock = MagicMock()
graph_planner_models_mock = MagicMock()

# Set up nested structure
graph_mock.trading_graph = graph_trading_graph_mock
graph_mock.planner = graph_planner_mock
graph_planner_mock.models = graph_planner_models_mock

# Mock ExecutionPlan class
graph_planner_models_mock.ExecutionPlan = MagicMock()

# Mock TradingAgentsGraph class
graph_trading_graph_mock.TradingAgentsGraph = MagicMock()

# Register mocks in sys.modules
sys.modules['graph'] = graph_mock
sys.modules['graph.trading_graph'] = graph_trading_graph_mock
sys.modules['graph.planner'] = graph_planner_mock
sys.modules['graph.planner.models'] = graph_planner_models_mock
sys.modules['agents_module'] = MagicMock()

# Import server app (adjust import path based on actual structure)
# The mocks above should allow server to import successfully
try:
    from server import app
except ImportError as e:
    # If import fails, create a minimal app for testing
    from fastapi import FastAPI
    app = FastAPI(title="Meridian Agents API Test")
    print(f"Warning: Could not import full server, using minimal app: {e}")
except Exception as e:
    # Catch any other errors during import (e.g., missing dependencies)
    from fastapi import FastAPI
    app = FastAPI(title="Meridian Agents API Test")
    print(f"Warning: Error importing server, using minimal app: {e}")


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
    # Create a minimal aggregated_context mock
    aggregated_context_mock = MagicMock()
    aggregated_context_mock.execution_plan = None
    
    # Create a minimal synthesizer_output mock
    synthesizer_output_mock = MagicMock()
    
    # Create mock
    mock = Mock()
    
    # Use AsyncMock so we can set side_effect for error testing
    # Default behavior: return the tuple
    # Tests can override with side_effect to raise exceptions
    async def default_propagate(company_name, trade_date, query=None, context=None):
        return (
            {"test": "state", "company_of_interest": company_name, "trade_date": trade_date},
            "BUY",
            aggregated_context_mock,
            synthesizer_output_mock
        )
    
    # Create AsyncMock with default coroutine function
    # Tests can override side_effect to raise exceptions
    mock.propagate = AsyncMock(side_effect=default_propagate)
    
    # Also mock enable_event_streaming which might be called
    mock.enable_event_streaming = MagicMock()
    
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

