# Running Unit Tests for Meridian Agents

This guide explains how to run unit tests for the Meridian Agents service.

## Prerequisites

1. **Python 3.11+** installed
2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```
3. **pytest and testing dependencies**:
   ```bash
   # Minimum required
   pip install pytest pytest-asyncio
   
   # For coverage reports (optional but recommended)
   pip install pytest-cov
   ```

## Quick Start

### Run All Tests

```bash
# From the meridian-agents directory
# Basic test run (no coverage)
pytest tests/ -v

# With coverage (requires pytest-cov)
pytest tests/ -v --cov=server --cov=models --cov=utils --cov-report=html
```

### Run with Coverage (Recommended)

**Note**: Coverage requires `pytest-cov` to be installed:
```bash
pip install pytest-cov
```

Then run:
```bash
# Run tests with coverage report
pytest tests/ -v --cov=server --cov=models --cov=utils --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

The coverage target is **> 70%** (when using coverage).

## Test Structure

The test suite currently contains **53 tests** across unit, integration, and evaluation tests.

### Unit Tests (in `tests/`)

- **`test_health.py`** - Health check endpoint tests
  - `TestHealthEndpointSuccess` - Successful health check scenarios
  - `TestHealthEndpointGraphError` - Health check with graph initialization errors
  - `TestHealthEndpointResponseTime` - Response time validation
  
- **`test_analyze.py`** - Analyze endpoint tests
  - `TestAnalyzeEndpointValidRequest` - Valid request handling
  - `TestAnalyzeEndpointWithContext` - Request with conversation context
  - `TestAnalyzeEndpointErrorHandling` - Error scenarios and edge cases
  
- **`test_logging.py`** - Logging functionality tests
  - `TestStructuredLogging` - JSON formatter and structured logging
  - `TestRequestIDGeneration` - Request ID format and uniqueness
  - `TestSensitiveDataSanitization` - API keys, passwords, tokens sanitization
  
- **`test_errors.py`** - Error handling and exception tests
  - `TestCustomExceptions` - Custom exception classes
  - `TestErrorResponse` - Error response formatting (dev/prod)
  - `TestErrorSanitization` - Error message sanitization
  - `TestHTTPExceptionHandling` - HTTP exception handling
  
- **`test_graph_init.py`** - Graph initialization tests
  - `TestThreadSafeGraphInitialization` - Thread-safe initialization, concurrent access, error handling

### Integration Tests (in `tests/integration/`)

- **`test_analyze_integration.py`** - Full integration tests for analyze endpoint
  - `TestAnalyzeEndpointIntegration` - End-to-end analyze workflow with and without context
  
- **`test_health_integration.py`** - Integration tests for health endpoint
  - `TestHealthEndpointIntegration` - Health check integration scenarios and multiple requests
  
- **`test_logging_integration.py`** - Integration tests for logging
  - `TestLoggingIntegration` - Logging across endpoints, error context logging
  
- **`test_error_handling.py`** - Integration error handling tests
  - `TestErrorHandlingIntegration` - Validation errors, server errors, error response structure, health endpoint error handling
  
- **`test_concurrent_requests.py`** - Concurrent request handling tests
  - `TestConcurrentRequests` - Concurrent health checks, concurrent analyze requests, mixed concurrent requests

### Agent Evaluations (in `tests/evals/`)

- **`eval_config.yaml`** - Configuration for agent evaluations
- **`run_eval.py`** - Evaluation runner script
- **`scorers.py`** - Scoring logic for agent responses
- **`reports/`** - Evaluation reports and results
- See `docs/agents/EVAL_DOCUMENTATION.md` for detailed agent evaluation documentation

## Running Specific Tests

### Run a Single Test File

```bash
# Run health tests only
pytest tests/test_health.py -v

# Run analyze tests only
pytest tests/test_analyze.py -v

# Run integration tests only
pytest tests/integration/ -v
```

### Run a Specific Test Function

```bash
# Run a specific test by name
pytest tests/test_health.py::TestHealthEndpointSuccess::test_health_endpoint_returns_200 -v
```

### Run Tests Matching a Pattern

```bash
# Run all tests with "health" in the name
pytest tests/ -k "health" -v

# Run all tests with "error" in the name
pytest tests/ -k "error" -v
```

## Test Markers

The project uses pytest markers (defined in `pytest.ini`):

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.requires_api` - Tests requiring external API access

### Run Tests by Marker

```bash
# Run only unit tests
pytest tests/ -m unit -v

# Run only integration tests
pytest tests/ -m integration -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Skip API-requiring tests
pytest tests/ -m "not requires_api" -v
```

## Configuration

The test configuration is in `pytest.ini`:

- **Test discovery**: `test_*.py` and `*_test.py` files
- **Test paths**: `tests/` directory
- **Coverage**: Tracks `server`, `models`, and `utils` modules (optional, requires `pytest-cov`)
- **Output**: Verbose mode with short tracebacks
- **Coverage target**: 70% minimum (when coverage is enabled)
- **Logging**: Live log output enabled at INFO level
- **Markers**: `unit`, `integration`, `slow`, `requires_api`

## Environment Variables

Tests automatically set mock environment variables via `conftest.py`:

- `OPENAI_API_KEY=test-api-key`
- `PORT=8001`
- `LOG_LEVEL=DEBUG`
- `ENVIRONMENT=testing`

You don't need to set these manually for unit tests.

## Common Test Commands

### Basic Test Run

```bash
# Simple test run
pytest tests/ -v
```

### With Coverage

```bash
# Coverage with terminal output
pytest tests/ --cov=server --cov=models --cov=utils --cov-report=term-missing

# Coverage with HTML report
pytest tests/ --cov=server --cov=models --cov=utils --cov-report=html
```

### Parallel Execution (if pytest-xdist installed)

```bash
# Run tests in parallel (faster)
pytest tests/ -n auto -v
```

### Stop on First Failure

```bash
# Stop immediately when a test fails
pytest tests/ -x -v
```

### Show Print Statements

```bash
# Show print() output during tests
pytest tests/ -s -v
```

### Verbose Output

```bash
# Very verbose output (shows each test name)
pytest tests/ -vv

# Show local variables on failure
pytest tests/ -l -v
```

## Test Fixtures

Common fixtures available (defined in `conftest.py`):

- **`client`** - FastAPI TestClient instance for making HTTP requests
- **`mock_graph`** - Mock TradingAgentsGraph with AsyncMock `propagate` method
  - Returns default state, decision, aggregated_context, and synthesizer_output
  - Supports `side_effect` override for error testing
- **`sample_analyze_request`** - Sample analyze request data (AAPL, 2024-12-19)
- **`sample_analyze_request_with_context`** - Sample request with conversation context
- **`mock_config`** - Auto-applied mock configuration (auto-use fixture)
  - Sets test environment variables automatically

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Make sure you're in the meridian-agents directory
cd meridian-agents

# Run from project root
pytest tests/ -v
```

### Missing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio pytest-mock
```

### Coverage Not Working

```bash
# Make sure pytest-cov is installed
pip install pytest-cov

# Run with explicit coverage
pytest tests/ --cov=server --cov=models --cov=utils
```

### Tests Failing Due to API Keys

Unit tests use mocks and don't require real API keys. If tests are trying to use real APIs:

1. Check that `conftest.py` is being loaded
2. Verify mocks are properly set up
3. Ensure `OPENAI_API_KEY` is set to a test value in fixtures

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run tests with coverage and fail if below threshold
pytest tests/ \
  --cov=server \
  --cov=models \
  --cov=utils \
  --cov-report=xml \
  --cov-report=term \
  --cov-fail-under=70 \
  -v
```

## Best Practices

1. **Run tests before committing**:
   ```bash
   pytest tests/ -v
   ```

2. **Check coverage regularly**:
   ```bash
   pytest tests/ --cov --cov-report=html
   ```

3. **Run integration tests separately** (they're slower):
   ```bash
   pytest tests/integration/ -v
   ```

4. **Use markers for test organization**:
   ```python
   @pytest.mark.unit
   def test_something():
       pass
   ```

## Example Test Run Output

```
tests/integration/test_analyze_integration.py::TestAnalyzeEndpointIntegration::test_analyze_endpoint_full_workflow PASSED
tests/integration/test_analyze_integration.py::TestAnalyzeEndpointIntegration::test_analyze_endpoint_with_context_workflow PASSED
tests/integration/test_concurrent_requests.py::TestConcurrentRequests::test_concurrent_health_checks PASSED
tests/integration/test_concurrent_requests.py::TestConcurrentRequests::test_concurrent_analyze_requests PASSED
tests/integration/test_concurrent_requests.py::TestConcurrentRequests::test_mixed_concurrent_requests PASSED
tests/integration/test_error_handling.py::TestErrorHandlingIntegration::test_validation_error_response PASSED
tests/integration/test_error_handling.py::TestErrorHandlingIntegration::test_server_error_response PASSED
tests/integration/test_error_handling.py::TestErrorHandlingIntegration::test_error_response_structure PASSED
tests/integration/test_error_handling.py::TestErrorHandlingIntegration::test_health_endpoint_error_handling PASSED
tests/integration/test_health_integration.py::TestHealthEndpointIntegration::test_health_endpoint_integration PASSED
tests/integration/test_health_integration.py::TestHealthEndpointIntegration::test_health_endpoint_multiple_requests PASSED
tests/integration/test_logging_integration.py::TestLoggingIntegration::test_health_endpoint_generates_logs PASSED
tests/integration/test_logging_integration.py::TestLoggingIntegration::test_analyze_endpoint_generates_logs PASSED
tests/integration/test_logging_integration.py::TestLoggingIntegration::test_error_logging_includes_context PASSED
tests/test_analyze.py::TestAnalyzeEndpointValidRequest::test_analyze_endpoint_with_valid_request PASSED
tests/test_analyze.py::TestAnalyzeEndpointValidRequest::test_analyze_endpoint_response_structure PASSED
tests/test_analyze.py::TestAnalyzeEndpointValidRequest::test_analyze_endpoint_response_values PASSED
tests/test_analyze.py::TestAnalyzeEndpointWithContext::test_analyze_endpoint_with_context PASSED
tests/test_analyze.py::TestAnalyzeEndpointWithContext::test_analyze_endpoint_processes_context PASSED
tests/test_analyze.py::TestAnalyzeEndpointErrorHandling::test_analyze_endpoint_graph_error PASSED
tests/test_analyze.py::TestAnalyzeEndpointErrorHandling::test_analyze_endpoint_analysis_error PASSED
tests/test_analyze.py::TestAnalyzeEndpointErrorHandling::test_analyze_endpoint_invalid_request PASSED
tests/test_analyze.py::TestAnalyzeEndpointErrorHandling::test_analyze_endpoint_missing_fields PASSED
tests/test_errors.py::TestCustomExceptions::test_agents_service_error PASSED
tests/test_errors.py::TestCustomExceptions::test_graph_initialization_error PASSED
tests/test_errors.py::TestCustomExceptions::test_analysis_error PASSED
tests/test_errors.py::TestCustomExceptions::test_validation_error PASSED
tests/test_errors.py::TestErrorResponse::test_create_error_response_development PASSED
tests/test_errors.py::TestErrorResponse::test_create_error_response_production PASSED
tests/test_errors.py::TestErrorSanitization::test_sanitize_error_with_api_key PASSED
tests/test_errors.py::TestErrorSanitization::test_sanitize_error_with_password PASSED
tests/test_errors.py::TestErrorSanitization::test_sanitize_error_normal_message PASSED
tests/test_errors.py::TestHTTPExceptionHandling::test_handle_http_exception_production PASSED
tests/test_errors.py::TestHTTPExceptionHandling::test_handle_http_exception_development PASSED
tests/test_graph_init.py::TestThreadSafeGraphInitialization::test_graph_initialized_once PASSED
tests/test_graph_init.py::TestThreadSafeGraphInitialization::test_concurrent_graph_initialization PASSED
tests/test_graph_init.py::TestThreadSafeGraphInitialization::test_graph_initialization_error_handling PASSED
tests/test_graph_init.py::TestThreadSafeGraphInitialization::test_graph_initialization_lock PASSED
tests/test_health.py::TestHealthEndpointSuccess::test_health_endpoint_returns_200 PASSED
tests/test_health.py::TestHealthEndpointSuccess::test_health_endpoint_structure PASSED
tests/test_health.py::TestHealthEndpointSuccess::test_health_endpoint_success_response PASSED
tests/test_health.py::TestHealthEndpointGraphError::test_health_endpoint_returns_200_on_graph_error PASSED
tests/test_health.py::TestHealthEndpointGraphError::test_health_endpoint_error_response PASSED
tests/test_health.py::TestHealthEndpointGraphError::test_health_endpoint_includes_error_message PASSED
tests/test_health.py::TestHealthEndpointResponseTime::test_health_endpoint_response_time_under_5_seconds PASSED
tests/test_logging.py::TestStructuredLogging::test_json_formatter_output PASSED
tests/test_logging.py::TestStructuredLogging::test_json_formatter_with_request_id PASSED
tests/test_logging.py::TestStructuredLogging::test_json_formatter_with_error_context PASSED
tests/test_logging.py::TestRequestIDGeneration::test_request_id_format PASSED
tests/test_logging.py::TestRequestIDGeneration::test_request_id_uniqueness PASSED
tests/test_logging.py::TestSensitiveDataSanitization::test_sanitize_api_key PASSED
tests/test_logging.py::TestSensitiveDataSanitization::test_sanitize_password PASSED
tests/test_logging.py::TestSensitiveDataSanitization::test_sanitize_token PASSED
...
============================== 53 passed in 0.27s =========================
```

## Test Statistics

- **Total Tests**: 53 tests
- **Unit Tests**: ~30 tests
- **Integration Tests**: ~15 tests
- **Evaluation Tests**: 11 agents × multiple test cases
- **Test Execution Time**: ~0.27s (all tests)

## Additional Resources

- **pytest.ini**: Test configuration and markers
- **conftest.py**: Shared fixtures, mocks, and test setup
- **README.md**: Main project documentation
- **docs/agents/EVAL_DOCUMENTATION.md**: Detailed agent evaluation documentation
- **tests/evals/eval_config.yaml**: Agent evaluation configuration
- **tests/evals/run_eval.py**: Evaluation runner script

