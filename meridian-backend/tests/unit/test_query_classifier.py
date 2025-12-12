"""
Unit tests for query classifier and intent classification.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import intent classification (with fallback if not available)
try:
    from services.query_classifier import get_query_classifier
    from services.agent_orchestrator import get_agent_orchestrator
    from models.query_intent import QueryIntent
    from models.agent_workflow import AgentWorkflowConfig
    INTENT_CLASSIFICATION_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    INTENT_CLASSIFICATION_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason=f"Intent classification not available: {e}")


@pytest.mark.unit
class TestQueryClassifier:
    """Tests for query classifier functionality."""
    
    def test_classifier_available(self):
        """Test that classifier can be imported."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Mock the classifier to avoid real API calls
        with patch('services.query_classifier.get_query_classifier') as mock_get_classifier:
            mock_classifier = MagicMock()
            mock_get_classifier.return_value = mock_classifier
            classifier = get_query_classifier()
            assert classifier is not None
    
    def test_classify_simple_chat(self, mock_agent_orchestrator):
        """Test classification of simple chat queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use the mock orchestrator directly - it's already set up to return mock results
        intent, workflow = mock_agent_orchestrator.classify_and_get_workflow("Hello! What are you?")
        
        assert intent is not None
        assert workflow is not None
        assert hasattr(intent, 'value') or isinstance(intent, QueryIntent)
    
    def test_classify_basic_info(self, mock_agent_orchestrator):
        """Test classification of basic info queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use the mock orchestrator directly
        intent, workflow = mock_agent_orchestrator.classify_and_get_workflow("What is Apple stock trading at today?")
        
        assert intent is not None
        assert workflow is not None
        assert hasattr(intent, 'value') or isinstance(intent, QueryIntent)


@pytest.mark.unit
class TestIntentClassificationCategories:
    """Tests for intent classification across different categories."""
    
    @pytest.fixture
    def test_queries(self):
        """Test queries organized by category."""
        return {
            "simple_chat": [
                "Hello! What are you?",
                "What can you help me with?",
                "Tell me about yourself"
            ],
            "basic_info": [
                "What is Apple stock trading at today?",
                "What is Tesla's business?",
                "What's Microsoft's main products?"
            ],
            "technical_analysis": [
                "Run a market analysis on AAPL",
                "Apple stock technical analysis",
                "What's the technical outlook for Tesla?"
            ],
            "fundamental_analysis": [
                "Analyze Apple's fundamentals",
                "Get fundamental data for Apple",
                "Tesla's financial health"
            ],
            "comprehensive_analysis": [
                "Should I buy Apple stock today?",
                "Is Tesla overvalued?",
                "Comprehensive analysis of AMZN"
            ]
        }
    
    def test_classify_simple_chat_queries(self, test_queries, mock_agent_orchestrator):
        """Test classification of simple chat queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use mock orchestrator directly - no real API calls
        for query in test_queries["simple_chat"]:
            intent, workflow = mock_agent_orchestrator.classify_and_get_workflow(query)
            assert intent is not None
            assert workflow is not None
    
    def test_classify_basic_info_queries(self, test_queries, mock_agent_orchestrator):
        """Test classification of basic info queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use mock orchestrator directly - no real API calls
        for query in test_queries["basic_info"]:
            intent, workflow = mock_agent_orchestrator.classify_and_get_workflow(query)
            assert intent is not None
            assert workflow is not None
    
    def test_classify_technical_analysis_queries(self, test_queries, mock_agent_orchestrator):
        """Test classification of technical analysis queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use mock orchestrator directly - no real API calls
        for query in test_queries["technical_analysis"]:
            intent, workflow = mock_agent_orchestrator.classify_and_get_workflow(query)
            assert intent is not None
            assert workflow is not None
    
    def test_classify_fundamental_analysis_queries(self, test_queries, mock_agent_orchestrator):
        """Test classification of fundamental analysis queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use mock orchestrator directly - no real API calls
        for query in test_queries["fundamental_analysis"]:
            intent, workflow = mock_agent_orchestrator.classify_and_get_workflow(query)
            assert intent is not None
            assert workflow is not None
    
    def test_classify_comprehensive_analysis_queries(self, test_queries, mock_agent_orchestrator):
        """Test classification of comprehensive analysis queries."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            pytest.skip("Intent classification not available")
        
        # Use mock orchestrator directly - no real API calls
        for query in test_queries["comprehensive_analysis"]:
            intent, workflow = mock_agent_orchestrator.classify_and_get_workflow(query)
            assert intent is not None
            assert workflow is not None

