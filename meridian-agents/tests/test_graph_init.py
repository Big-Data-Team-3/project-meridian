"""
Unit tests for thread-safe graph initialization.
"""
import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from server import get_graph, _graph_instance, _graph_lock, _graph_initializing


class TestThreadSafeGraphInitialization:
    """Tests for thread-safe graph initialization."""
    
    def test_graph_initialized_once(self):
        """Test that graph is initialized only once even with multiple calls."""
        # Reset global state
        import server
        server._graph_instance = None
        server._graph_initializing = False
        server._graph_init_error = None
        
        mock_graph = Mock()
        with patch("server.TradingAgentsGraph", return_value=mock_graph):
            # Call get_graph multiple times
            graph1 = get_graph()
            graph2 = get_graph()
            graph3 = get_graph()
            
            # All should return the same instance
            assert graph1 is graph2
            assert graph2 is graph3
            assert graph1 is mock_graph
    
    def test_concurrent_graph_initialization(self):
        """Test that concurrent calls don't cause race conditions."""
        # Reset global state
        import server
        server._graph_instance = None
        server._graph_initializing = False
        server._graph_init_error = None
        
        mock_graph = Mock()
        initialization_times = []
        
        def init_graph():
            start = time.time()
            with patch("server.TradingAgentsGraph", return_value=mock_graph):
                graph = get_graph()
                initialization_times.append(time.time() - start)
                return graph
        
        # Create multiple threads
        threads = []
        results = []
        
        for _ in range(10):
            thread = threading.Thread(target=lambda: results.append(init_graph()))
            threads.append(thread)
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should return the same graph instance
        assert len(set(id(r) for r in results)) == 1, "All threads should get the same graph instance"
        assert all(r is mock_graph for r in results)
    
    def test_graph_initialization_error_handling(self):
        """Test that graph initialization errors are handled gracefully."""
        # Reset global state
        import server
        server._graph_instance = None
        server._graph_initializing = False
        server._graph_init_error = None
        
        with patch("server.TradingAgentsGraph", side_effect=Exception("Init failed")):
            with pytest.raises(Exception):
                get_graph()
            
            # Should not have a graph instance
            assert server._graph_instance is None
    
    def test_graph_initialization_lock(self):
        """Test that graph initialization uses proper locking."""
        # Reset global state
        import server
        server._graph_instance = None
        server._graph_initializing = False
        server._graph_init_error = None
        
        # Verify lock exists
        assert hasattr(server, "_graph_lock")
        assert hasattr(server._graph_lock, "acquire")  # Check it's a lock-like object
        
        mock_graph = Mock()
        with patch("server.TradingAgentsGraph", return_value=mock_graph):
            # Lock should be acquired during initialization
            graph = get_graph()
            assert graph is not None

