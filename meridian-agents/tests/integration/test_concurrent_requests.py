"""
Integration tests for concurrent requests.
"""
import pytest
import threading
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestConcurrentRequests:
    """Tests for handling concurrent requests."""
    
    def test_concurrent_health_checks(self, client, mock_graph):
        """Test that multiple concurrent health checks work correctly."""
        results = []
        
        def make_request():
            with patch("server.get_graph", return_value=mock_graph):
                response = client.get("/health")
                results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should return 200
        assert all(status == 200 for status in results)
        assert len(results) == 10
    
    def test_concurrent_analyze_requests(self, client, mock_graph):
        """Test that multiple concurrent analyze requests work correctly."""
        results = []
        
        def make_request():
            with patch("server.get_graph", return_value=mock_graph):
                response = client.post(
                    "/analyze",
                    json={"company_name": "AAPL", "trade_date": "2024-12-19"}
                )
                results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should return 200
        assert all(status == 200 for status in results)
        assert len(results) == 5
    
    def test_mixed_concurrent_requests(self, client, mock_graph):
        """Test mixed concurrent health and analyze requests."""
        results = []
        
        def make_health_request():
            with patch("server.get_graph", return_value=mock_graph):
                response = client.get("/health")
                results.append(("health", response.status_code))
        
        def make_analyze_request():
            with patch("server.get_graph", return_value=mock_graph):
                response = client.post(
                    "/analyze",
                    json={"company_name": "AAPL", "trade_date": "2024-12-19"}
                )
                results.append(("analyze", response.status_code))
        
        # Create mixed threads
        threads = []
        for i in range(10):
            if i % 2 == 0:
                thread = threading.Thread(target=make_health_request)
            else:
                thread = threading.Thread(target=make_analyze_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should return 200
        assert all(status == 200 for _, status in results)
        assert len(results) == 10

