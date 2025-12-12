"""
Integration tests for health check endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpointIntegration:
    """Integration tests for health endpoint."""
    
    def test_health_endpoint_integration(self, client):
        """Test health endpoint with actual app instance."""
        response = client.get("/health")
        
        # Should always return 200
        assert response.status_code == 200
        
        # Should have required fields
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "graph_initialized" in data
    
    def test_health_endpoint_multiple_requests(self, client):
        """Test that health endpoint handles multiple requests."""
        responses = []
        for _ in range(5):
            response = client.get("/health")
            responses.append(response)
        
        # All should return 200
        assert all(r.status_code == 200 for r in responses)
        
        # All should have same structure
        for response in responses:
            data = response.json()
            assert "status" in data
            assert "service" in data
            assert "graph_initialized" in data

