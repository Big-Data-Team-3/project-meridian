# Backend Test Documentation

This document provides a comprehensive overview of all tests in the meridian-backend project, organized by category and purpose.

## Table of Contents

- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [Database Tests](#database-tests)
- [Test Fixtures](#test-fixtures)
- [Test Configuration](#test-configuration)
- [Best Practices](#best-practices)

---

## Running Tests

### Prerequisites

1. **Python 3.11+** installed
2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Test dependencies**:
   ```bash
   pip install pytest pytest-asyncio pytest-cov pytest-mock
   ```

### Basic Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=api --cov=services --cov=database --cov=models --cov=utils --cov-report=html

# Run only unit tests
pytest tests/unit/ -v -m unit

# Run only integration tests
pytest tests/integration/ -v -m integration

# Run specific test file
pytest tests/unit/test_query_classifier.py -v

# Run specific test function
pytest tests/unit/test_query_classifier.py::TestQueryClassifier::test_classifier_available -v

# Run tests matching a pattern
pytest tests/ -k "database" -v
```

### Test Markers

The project uses pytest markers to categorize tests:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may require external services)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.requires_api` - Tests requiring external API access
- `@pytest.mark.requires_db` - Tests requiring database connection
- `@pytest.mark.requires_gcp` - Tests requiring GCP credentials

**Run tests by marker:**
```bash
# Run only unit tests
pytest tests/ -m unit -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Skip database tests
pytest tests/ -m "not requires_db" -v
```

---

## Test Structure

```
meridian-backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures and configuration
│   ├── unit/                # Unit tests
│   │   ├── __init__.py
│   │   └── test_query_classifier.py
│   ├── integration/        # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   └── test_database.py
│   └── fixtures/            # Test fixtures and data
├── database/
│   ├── test_connection.py
│   └── test_crud_operations.py
├── test_user_query_intents.py
└── pytest.ini               # Pytest configuration
```

---

## Unit Tests

### 1. `tests/unit/test_query_classifier.py`

**Purpose**: Tests query classification and intent detection functionality.

**Test Coverage**:
- ✅ `TestQueryClassifier` - Basic classifier functionality
  - `test_classifier_available()` - Verifies classifier can be imported
  - `test_classify_simple_chat()` - Classifies simple chat queries
  - `test_classify_basic_info()` - Classifies basic information queries

- ✅ `TestIntentClassificationCategories` - Category-based classification
  - Tests classification across multiple categories:
    - Simple chat queries
    - Basic info queries
    - Technical analysis queries
    - Fundamental analysis queries
    - Comprehensive analysis queries

**Key Features**:
- Uses mock agent orchestrator to avoid real API calls
- Tests intent classification accuracy
- Validates workflow generation
- Handles cases where intent classification is not available

**Example Test**:
```python
def test_classify_simple_chat(self, mock_agent_orchestrator):
    """Test classification of simple chat queries."""
    intent, workflow = mock_agent_orchestrator.classify_and_get_workflow("Hello! What are you?")
    assert intent is not None
    assert workflow is not None
```

---

## Integration Tests

### 2. `tests/integration/test_api.py`

**Purpose**: Tests API endpoints end-to-end.

**Test Coverage**:
- ✅ `TestHealthEndpoint` - Health check endpoint
  - `test_health_endpoint()` - Verifies `/api/health` returns 200 with status

- ✅ `TestAuthEndpoint` - Authentication endpoints
  - `test_auth_endpoint_structure()` - Verifies auth endpoint structure

- ✅ `TestThreadsEndpoint` - Thread management endpoints
  - `test_threads_endpoint_requires_auth()` - Verifies authentication requirement

- ✅ `TestChatEndpoint` - Chat endpoints
  - `test_chat_endpoint_requires_auth()` - Verifies authentication requirement

**Key Features**:
- Uses FastAPI TestClient for HTTP requests
- Tests authentication requirements
- Validates response status codes
- Tests endpoint structure

**Example Test**:
```python
def test_health_endpoint(self, client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
```

---

### 3. `tests/integration/test_database.py`

**Purpose**: Tests database connection and CRUD operations with real Cloud SQL.

**Test Coverage**:
- ✅ `TestDatabaseConnection` - Connection tests
  - Tests Cloud SQL connection
  - Verifies database connectivity
  - Checks PostgreSQL version

- ✅ `TestTableExistence` - Schema validation
  - Verifies required tables exist (threads, messages)
  - Checks table structure

- ✅ `TestCRUDOperations` - Database operations
  - CREATE operations (INSERT)
  - READ operations (SELECT)
  - UPDATE operations
  - DELETE operations

- ✅ `TestMessageOperations` - Message-specific operations
  - Create messages
  - Retrieve messages by thread
  - Update messages
  - Delete messages

**Key Features**:
- Requires real database connection (`@pytest.mark.requires_db`)
- Requires GCP credentials (`@pytest.mark.requires_gcp`)
- Uses async/await for database operations
- Tests transaction handling
- Validates data integrity

**Prerequisites**:
- GCP credentials configured (`GOOGLE_APPLICATION_CREDENTIALS`)
- Database environment variables set
- Cloud SQL instance accessible
- Database migrations run

**Example Test**:
```python
@pytest.mark.requires_db
@pytest.mark.requires_gcp
async def test_create_thread(self):
    """Test creating a new thread."""
    # Test implementation
```

---

## Database Tests

### 4. `database/test_connection.py`

**Purpose**: Standalone script to verify Cloud SQL connection.

**Functionality**:
- Tests basic database connection
- Verifies database name
- Checks PostgreSQL version
- Lists available tables

**Usage**:
```bash
python database/test_connection.py
```

**Key Features**:
- Standalone script (not part of pytest suite)
- Quick connection verification
- Useful for debugging connection issues

---

### 5. `database/test_crud_operations.py`

**Purpose**: Comprehensive test script for all database CRUD operations.

**Test Coverage**:
- ✅ Connection test
- ✅ Table existence check
- ✅ CREATE operations
- ✅ READ operations
- ✅ UPDATE operations
- ✅ DELETE operations
- ✅ Message operations
- ✅ Transaction handling

**Usage**:
```bash
python database/test_crud_operations.py
```

**Key Features**:
- Comprehensive database testing
- Async/await support
- Detailed output for each test
- Error handling and reporting

---

## Intent Classification Tests

### 6. `test_user_query_intents.py`

**Purpose**: Comprehensive test suite for intent classification accuracy.

**Test Coverage**:
- ✅ Multiple query categories:
  - Simple chat queries
  - Basic info queries
  - Technical analysis queries
  - Fundamental analysis queries
  - Comprehensive analysis queries
  - Trading queries
  - Risk management queries

- ✅ Classification accuracy testing
- ✅ Workflow generation validation
- ✅ Instructor-based LLM classification

**Key Features**:
- Category-based test organization
- Expected intent validation
- Classification method verification
- Detailed test reporting

**Usage**:
```bash
# Run all tests
python test_user_query_intents.py

# Run specific category
python test_user_query_intents.py --category simple_chat

# Generate report
python test_user_query_intents.py --output report.json
```

---

## Test Fixtures

### `tests/conftest.py`

**Purpose**: Shared fixtures and test configuration.

**Available Fixtures**:

1. **`client`** - FastAPI TestClient
   ```python
   def test_something(client):
       response = client.get("/api/health")
   ```

2. **`mock_config`** (auto-use) - Mock configuration
   - Sets test environment variables
   - Automatically applied to all tests
   - Preserves real DB config for integration tests

3. **`mock_db_client`** - Mock database client
   ```python
   def test_something(mock_db_client):
       # Use mock_db_client for testing
   ```

4. **`mock_query_classifier`** - Mock query classifier
   ```python
   def test_something(mock_query_classifier):
       # Use mock_query_classifier for testing
   ```

5. **`mock_agent_orchestrator`** - Mock agent orchestrator
   ```python
   def test_something(mock_agent_orchestrator):
       intent, workflow = mock_agent_orchestrator.classify_and_get_workflow("query")
   ```

6. **`mock_openai_service`** - Mock OpenAI service
   ```python
   def test_something(mock_openai_service):
       # Use mock_openai_service for testing
   ```

7. **`sample_thread_data`** - Sample thread data
   ```python
   def test_something(sample_thread_data):
       thread_id = sample_thread_data["thread_id"]
   ```

8. **`sample_message_data`** - Sample message data
   ```python
   def test_something(sample_message_data):
       message_id = sample_message_data["message_id"]
   ```

9. **`sample_chat_request`** - Sample chat request
   ```python
   def test_something(sample_chat_request, client):
       response = client.post("/api/chat", json=sample_chat_request)
   ```

---

## Test Configuration

### `pytest.ini`

**Configuration Options**:
- **Test Discovery**: `test_*.py` and `*_test.py` files
- **Test Paths**: `tests/` directory
- **Output**: Verbose mode with short tracebacks
- **Async Mode**: Auto (`--asyncio-mode=auto`)
- **Logging**: Live log output at INFO level
- **Coverage**: Tracks `api`, `services`, `database`, `models`, `utils` modules

**Coverage Configuration** (optional):
```ini
--cov=api
--cov=services
--cov=database
--cov=models
--cov=utils
--cov-report=html
--cov-fail-under=70
```

---

## Environment Variables

### Test Environment Variables

Tests automatically set mock environment variables via `conftest.py`:

- `OPENAI_API_KEY=test-api-key`
- `PORT=8000`
- `LOG_LEVEL=DEBUG`
- `ENVIRONMENT=testing`
- `AGENTS_SERVICE_URL=http://localhost:8001`
- `DB_HOST=test-host` (only for non-integration tests)
- `DB_USER=test-user` (only for non-integration tests)
- `DB_PASSWORD=test-password` (only for non-integration tests)
- `DB_NAME=test-db` (only for non-integration tests)

### Database Integration Tests

For database integration tests, use `.env` file:

**Option 1: Use .env file (Recommended)**
```bash
# Create .env file in project root
cp .env.example .env
# Edit .env with your actual database credentials

# Tests will automatically load .env file
pytest tests/integration/test_database.py -v -m "requires_db and requires_gcp"
```

**Option 2: Set environment variables manually**
```bash
export INSTANCE_CONNECTION_NAME="project:region:instance"
export DB_USER="your_db_user"
export DB_PASS="your_db_password"
export DB_NAME="your_db_name"
export DB_TYPE="postgresql"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

pytest tests/integration/test_database.py -v -m "requires_db and requires_gcp"
```

**Note**: The `.env` file is searched in:
1. Project root directory (`project-meridian/.env`)
2. Backend directory (`meridian-backend/.env`)
3. Current working directory

---

## Best Practices

### 1. **Use Appropriate Test Markers**

```python
@pytest.mark.unit
def test_fast_unit_test():
    """Fast unit test that doesn't require external services."""
    pass

@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.requires_gcp
async def test_database_operation():
    """Integration test requiring database."""
    pass
```

### 2. **Mock External Dependencies**

```python
@patch('services.openai_service.get_openai_client')
def test_something(mock_openai):
    """Mock external API calls."""
    mock_openai.return_value.chat_completion.return_value = {"response": "test"}
    # Test implementation
```

### 3. **Use Fixtures for Common Setup**

```python
def test_something(client, sample_thread_data):
    """Use fixtures for common test data."""
    response = client.post("/api/threads", json=sample_thread_data)
    assert response.status_code == 200
```

### 4. **Clean Up After Tests**

```python
@pytest.fixture(autouse=True)
def cleanup():
    """Auto-cleanup after each test."""
    yield
    # Cleanup code here
```

### 5. **Test Async Code Properly**

```python
@pytest.mark.asyncio
async def test_async_function():
    """Use pytest-asyncio for async tests."""
    result = await some_async_function()
    assert result is not None
```

### 6. **Use Descriptive Test Names**

```python
# ✅ Good
def test_create_thread_with_valid_data_returns_201():
    pass

# ❌ Bad
def test_thread():
    pass
```

### 7. **Test Error Cases**

```python
def test_create_thread_with_invalid_data_returns_400():
    """Test error handling."""
    response = client.post("/api/threads", json={})
    assert response.status_code == 400
```

---

## Common Issues and Solutions

### Issue: Import Errors

**Solution**: Make sure you're running tests from the correct directory:
```bash
cd meridian-backend
pytest tests/ -v
```

### Issue: Database Tests Failing

**Solution**: Ensure:
1. GCP credentials are set (`GOOGLE_APPLICATION_CREDENTIALS`)
2. Database environment variables are configured
3. Cloud SQL instance is accessible
4. Migrations are run (`python database/run_migrations.py`)

**Skip database tests**:
```bash
pytest tests/ -m "not requires_db" -v
```

### Issue: Coverage Not Working

**Solution**: Install pytest-cov:
```bash
pip install pytest-cov
pytest tests/ --cov=api --cov=services --cov=database --cov=models --cov=utils
```

### Issue: Async Tests Not Running

**Solution**: Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

The `pytest.ini` is configured with `--asyncio-mode=auto` for automatic async support.

### Issue: Tests Trying to Use Real APIs

**Solution**: Check that mocks are properly set up in `conftest.py` and that test markers are correctly applied.

---

## Coverage Goals

Current coverage targets:

- **Minimum Coverage**: 70%
- **Coverage Modules**:
  - `api` - API endpoints
  - `services` - Business logic services
  - `database` - Database operations
  - `models` - Data models
  - `utils` - Utility functions

**Generate Coverage Report**:
```bash
pytest tests/ \
  --cov=api \
  --cov=services \
  --cov=database \
  --cov=models \
  --cov=utils \
  --cov-report=html \
  --cov-report=term-missing
```

---

## Continuous Integration

For CI/CD pipelines:

```bash
pytest tests/ \
  --cov=api \
  --cov=services \
  --cov=database \
  --cov=models \
  --cov=utils \
  --cov-report=xml \
  --cov-report=term \
  --cov-fail-under=70 \
  -v \
  -m "not requires_db or not requires_gcp"
```

This command:
- Runs all tests except those requiring database/GCP
- Generates coverage reports
- Fails if coverage is below 70%
- Outputs XML for CI integration

---

## Test Statistics

- **Total Test Files**: 7
- **Unit Tests**: 1 file (`tests/unit/test_query_classifier.py`)
- **Integration Tests**: 2 files (`tests/integration/test_api.py`, `tests/integration/test_database.py`)
- **Database Tests**: 2 files (`database/test_connection.py`, `database/test_crud_operations.py`)
- **Intent Classification Tests**: 1 file (`test_user_query_intents.py`)
- **Shared Fixtures**: 1 file (`tests/conftest.py`)

---

## Additional Resources

- **pytest.ini**: Test configuration
- **conftest.py**: Shared fixtures and test setup
- **tests/README.md**: Quick start guide for running tests
- **database/README_TESTING.md**: Database testing guide (if available)

---

## Quick Reference

### Run All Tests
```bash
pytest tests/ -v
```

### Run Unit Tests Only
```bash
pytest tests/unit/ -v -m unit
```

### Run Integration Tests Only
```bash
pytest tests/integration/ -v -m integration
```

### Run with Coverage
```bash
pytest tests/ --cov --cov-report=html
```

### Run Specific Test
```bash
pytest tests/unit/test_query_classifier.py::TestQueryClassifier::test_classifier_available -v
```

### Skip Slow Tests
```bash
pytest tests/ -m "not slow" -v
```

### Skip Database Tests
```bash
pytest tests/ -m "not requires_db" -v
```

---

*Last Updated: Based on current codebase structure*

