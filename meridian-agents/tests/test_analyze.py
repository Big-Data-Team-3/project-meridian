"""
Unit tests for analyze endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAnalyzeEndpointValidRequest:
    """Tests for analyze endpoint with valid requests."""
    
    def test_analyze_endpoint_with_valid_request(self, client, mock_graph, sample_analyze_request):
        """Test analyze endpoint with valid request."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=sample_analyze_request)
            assert response.status_code == 200
    
    def test_analyze_endpoint_response_structure(self, client, mock_graph, sample_analyze_request):
        """Test that analyze endpoint returns correct structure."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=sample_analyze_request)
            data = response.json()
            
            assert "company" in data
            assert "date" in data
            assert "decision" in data
            assert "state" in data
    
    def test_analyze_endpoint_response_values(self, client, mock_graph, sample_analyze_request):
        """Test analyze endpoint response values."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=sample_analyze_request)
            data = response.json()
            
            assert data["company"] == sample_analyze_request["company_name"]
            assert data["date"] == sample_analyze_request["trade_date"]
            assert data["decision"] == "BUY"  # From mock_graph fixture
            assert isinstance(data["state"], dict)


class TestAnalyzeEndpointWithContext:
    """Tests for analyze endpoint with conversation context."""
    
    def test_analyze_endpoint_with_context(self, client, mock_graph, sample_analyze_request_with_context):
        """Test analyze endpoint with conversation context."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=sample_analyze_request_with_context)
            assert response.status_code == 200
    
    def test_analyze_endpoint_processes_context(self, client, mock_graph, sample_analyze_request_with_context):
        """Test that conversation context is processed."""
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=sample_analyze_request_with_context)
            data = response.json()
            
            # Should still return valid response
            assert "company" in data
            assert "decision" in data


class TestAnalyzeEndpointErrorHandling:
    """Tests for analyze endpoint error handling."""
    
    def test_analyze_endpoint_graph_error(self, client, sample_analyze_request):
        """Test analyze endpoint with graph initialization error."""
        with patch("server.get_graph", side_effect=Exception("Graph init failed")):
            response = client.post("/analyze", json=sample_analyze_request)
            # Should return 500 on error
            assert response.status_code == 500
    
    def test_analyze_endpoint_analysis_error(self, client, mock_graph, sample_analyze_request):
        """Test analyze endpoint with analysis error."""
        mock_graph.propagate.side_effect = Exception("Analysis failed")
        with patch("server.get_graph", return_value=mock_graph):
            response = client.post("/analyze", json=sample_analyze_request)
            assert response.status_code == 500
    
    def test_analyze_endpoint_invalid_request(self, client):
        """Test analyze endpoint with invalid request."""
        response = client.post("/analyze", json={"invalid": "data"})
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_analyze_endpoint_missing_fields(self, client):
        """Test analyze endpoint with missing required fields."""
        response = client.post("/analyze", json={"company_name": "AAPL"})
        # Should return 422 for missing trade_date
        assert response.status_code == 422

