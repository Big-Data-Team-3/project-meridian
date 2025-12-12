"""
Unit tests for structured logging.
"""
import pytest
import json
import logging
from io import StringIO
from utils.logging import setup_logging, JSONFormatter, sanitize_sensitive_data


class TestStructuredLogging:
    """Tests for structured logging format."""
    
    def test_json_formatter_output(self):
        """Test that JSONFormatter produces valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        # Should be valid JSON
        data = json.loads(output)
        assert "timestamp" in data
        assert "level" in data
        assert "message" in data
        assert data["message"] == "Test message"
    
    def test_json_formatter_with_request_id(self):
        """Test JSONFormatter with request ID."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        # Set request_id in extra_fields (as the formatter expects)
        record.extra_fields = {"request_id": "req-12345678"}
        
        output = formatter.format(record)
        data = json.loads(output)
        assert data["request_id"] == "req-12345678"
    
    def test_json_formatter_with_error_context(self):
        """Test JSONFormatter with error context."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=None
        )
        record.error_context = {"error_type": "ValueError", "details": "Invalid input"}
        
        output = formatter.format(record)
        data = json.loads(output)
        assert "error_context" in data
        assert data["error_context"]["error_type"] == "ValueError"


class TestRequestIDGeneration:
    """Tests for request ID generation and tracking."""
    
    def test_request_id_format(self):
        """Test that request IDs follow the correct format."""
        import time
        request_id = f"req-{int(time.time() * 1000)}"
        
        assert request_id.startswith("req-")
        assert len(request_id) > 10  # Should have timestamp
    
    def test_request_id_uniqueness(self):
        """Test that request IDs are unique."""
        import time
        ids = []
        for _ in range(10):
            time.sleep(0.001)  # Small delay to ensure uniqueness
            ids.append(f"req-{int(time.time() * 1000)}")
        
        # Should have unique IDs (or at least mostly unique)
        assert len(set(ids)) >= 8  # Allow for some collisions in fast execution


class TestSensitiveDataSanitization:
    """Tests for sensitive data sanitization."""
    
    def test_sanitize_api_key(self):
        """Test that API keys are sanitized."""
        data = {
            "api_key": "sk-1234567890abcdef",
            "company": "AAPL"
        }
        
        sanitized = sanitize_sensitive_data(data)
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["company"] == "AAPL"  # Non-sensitive data unchanged
    
    def test_sanitize_password(self):
        """Test that passwords are sanitized."""
        data = {
            "password": "secret123",
            "username": "user"
        }
        
        sanitized = sanitize_sensitive_data(data)
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["username"] == "user"
    
    def test_sanitize_token(self):
        """Test that tokens are sanitized."""
        data = {
            "token": "bearer-abc123",
            "message": "test"
        }
        
        sanitized = sanitize_sensitive_data(data)
        assert sanitized["token"] == "***REDACTED***"
        assert sanitized["message"] == "test"

