"""
Integration tests for error handling.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestErrorHandlingIntegration:
    """Integration tests for error response format."""
    
    def test_validation_error_response(self, client):
        """Test that validation errors return 422."""
        response = client.post("/analyze", json={"invalid": "data"})
        assert response.status_code == 422
        assert "detail" in response.json()
    
    def test_server_error_response(self, client, sample_analyze_request):
        """Test that server errors return 500."""
        with patch("server.get_graph", side_effect=Exception("Server error")):
            response = client.post("/analyze", json=sample_analyze_request)
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    def test_error_response_structure(self, client, sample_analyze_request):
        """Test that error responses have proper structure."""
        with patch("server.get_graph", side_effect=Exception("Test error")):
            response = client.post("/analyze", json=sample_analyze_request)
            data = response.json()
            
            # Should have detail field
            assert "detail" in data
            # May have error_type in development
            assert isinstance(data["detail"], str)
    
    def test_health_endpoint_error_handling(self, client):
        """Test that health endpoint handles errors gracefully."""
        # Health endpoint checks _graph_init_error, not get_graph()
        # So we need to patch the global variable
        with patch("server._graph_init_error", Exception("Graph error")):
            response = client.get("/health")
            # Health should always return 200
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"

