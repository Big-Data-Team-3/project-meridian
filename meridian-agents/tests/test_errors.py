"""
Unit tests for error handling.
"""
import pytest
from utils.errors import (
    AgentsServiceError,
    GraphInitializationError,
    AnalysisError,
    ValidationError,
    create_error_response,
    sanitize_error_for_production,
    handle_http_exception
)
from fastapi import HTTPException
from unittest.mock import patch


class TestCustomExceptions:
    """Tests for custom exception classes."""
    
    def test_agents_service_error(self):
        """Test base AgentsServiceError."""
        error = AgentsServiceError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_graph_initialization_error(self):
        """Test GraphInitializationError."""
        error = GraphInitializationError("Graph init failed")
        assert str(error) == "Graph init failed"
        assert isinstance(error, AgentsServiceError)
    
    def test_analysis_error(self):
        """Test AnalysisError."""
        error = AnalysisError("Analysis failed")
        assert str(error) == "Analysis failed"
        assert isinstance(error, AgentsServiceError)
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, AgentsServiceError)


class TestErrorResponse:
    """Tests for error response creation."""
    
    def test_create_error_response_development(self):
        """Test error response in development mode."""
        with patch("utils.errors.get_config") as mock_config:
            mock_config.return_value.is_development = True
            error = ValueError("Test error")
            response = create_error_response(error, include_traceback=True)
            
            assert "detail" in response
            assert "error_type" in response
            assert response["error_type"] == "ValueError"
            assert "traceback" in response
    
    def test_create_error_response_production(self):
        """Test error response in production mode."""
        with patch("utils.errors.get_config") as mock_config:
            mock_config.return_value.is_development = False
            error = ValueError("Test error")
            response = create_error_response(error, include_traceback=False)
            
            assert "detail" in response
            assert "error_type" in response
            assert "traceback" not in response


class TestErrorSanitization:
    """Tests for error sanitization."""
    
    def test_sanitize_error_with_api_key(self):
        """Test that errors with API keys are sanitized."""
        error = Exception("Error with api_key: sk-1234567890")
        sanitized = sanitize_error_for_production(error)
        assert "api_key" not in sanitized.lower()
        assert sanitized == "An internal error occurred"
    
    def test_sanitize_error_with_password(self):
        """Test that errors with passwords are sanitized."""
        error = Exception("Error with password: secret123")
        sanitized = sanitize_error_for_production(error)
        assert "password" not in sanitized.lower()
        assert sanitized == "An internal error occurred"
    
    def test_sanitize_error_normal_message(self):
        """Test that normal error messages are preserved."""
        error = Exception("File not found")
        sanitized = sanitize_error_for_production(error)
        assert sanitized == "File not found"


class TestHTTPExceptionHandling:
    """Tests for HTTP exception handling."""
    
    def test_handle_http_exception_production(self):
        """Test HTTP exception handling in production."""
        with patch("utils.errors.get_config") as mock_config:
            mock_config.return_value.is_production = True
            error = ValueError("Test error")
            http_exception = handle_http_exception(error, status_code=500)
            
            assert isinstance(http_exception, HTTPException)
            assert http_exception.status_code == 500
            # In production, should sanitize
            assert "Test error" in http_exception.detail or "internal error" in http_exception.detail.lower()
    
    def test_handle_http_exception_development(self):
        """Test HTTP exception handling in development."""
        with patch("utils.errors.get_config") as mock_config:
            mock_config.return_value.is_production = False
            error = ValueError("Test error")
            http_exception = handle_http_exception(error, status_code=400)
            
            assert isinstance(http_exception, HTTPException)
            assert http_exception.status_code == 400
            assert "Test error" in http_exception.detail

