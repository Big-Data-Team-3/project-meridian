"""
Unit tests for health check endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpointSuccess:
    """Tests for successful health check."""
    
    def test_health_endpoint_returns_200(self, client, mock_graph):
        """Test that health endpoint returns HTTP 200."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_health_endpoint_structure(self, client, mock_graph):
        """Test that health endpoint returns correct structure."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.get("/health")
            data = response.json()
            
            assert "status" in data
            assert "service" in data
            assert "graph_initialized" in data
            assert data["service"] == "meridian-agents"
    
    def test_health_endpoint_success_response(self, client, mock_graph):
        """Test successful health check response."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.get("/health")
            data = response.json()
            
            assert data["status"] == "ok"
            assert data["graph_initialized"] is True
            assert data.get("error") is None


class TestHealthEndpointGraphError:
    """Tests for health endpoint with graph initialization errors."""
    
    def test_health_endpoint_returns_200_on_graph_error(self, client):
        """Test that health endpoint returns HTTP 200 even when graph fails."""
        with patch("server.get_graph", side_effect=Exception("Graph init failed")):
            response = client.get("/health")
            # Health endpoint MUST return 200 even on error (constitution requirement)
            assert response.status_code == 200
    
    def test_health_endpoint_error_response(self, client):
        """Test health endpoint response when graph initialization fails."""
        with patch("server.get_graph", side_effect=Exception("Graph init failed")):
            response = client.get("/health")
            data = response.json()
            
            assert data["status"] == "error"
            assert data["graph_initialized"] is False
            assert "error" in data
            assert data["error"] is not None
    
    def test_health_endpoint_includes_error_message(self, client):
        """Test that error message is included in response."""
        error_msg = "Failed to initialize graph"
        with patch("server.get_graph", side_effect=Exception(error_msg)):
            response = client.get("/health")
            data = response.json()
            
            assert error_msg in data["error"]


class TestHealthEndpointResponseTime:
    """Tests for health endpoint response time."""
    
    def test_health_endpoint_response_time_under_5_seconds(self, client, mock_graph):
        """Test that health endpoint responds within 5 seconds."""
        import time
        with patch("server.get_graph", return_value=mock_graph):
            start = time.time()
            response = client.get("/health")
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 5.0, f"Health check took {elapsed:.2f}s, must be < 5s"

