"""
Integration tests for analyze endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAnalyzeEndpointIntegration:
    """Integration tests for analyze endpoint."""
    
    def test_analyze_endpoint_full_workflow(self, client, mock_graph):
        """Test full analysis workflow."""
        from unittest.mock import patch
        
        request_data = {
            "company_name": "AAPL",
            "trade_date": "2024-12-19"
        }
        
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "company" in data
            assert "decision" in data
            assert "state" in data
    
    def test_analyze_endpoint_with_context_workflow(self, client, mock_graph):
        """Test analysis workflow with conversation context."""
        from unittest.mock import patch
        
        request_data = {
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
        
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["company"] == "AAPL"

