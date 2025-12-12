"""
Integration tests for Cloud SQL database operations.
These tests require a real database connection and GCP credentials.
"""
import pytest
import asyncio
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, AsyncMock
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables from .env file
# Try loading from project root first, then backend directory
project_root = Path(__file__).parent.parent.parent.parent
backend_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")
load_dotenv(dotenv_path=backend_dir / ".env")
load_dotenv()  # Also try current directory

# Resolve GOOGLE_APPLICATION_CREDENTIALS path if set
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    # Handle relative paths
    if credentials_path.startswith("./"):
        credentials_path = credentials_path[2:]
    
    # Try to resolve relative to project root
    if not os.path.isabs(credentials_path):
        # Try project root
        abs_path = project_root / credentials_path
        if abs_path.exists():
            credentials_path = str(abs_path.absolute())
        # Try backend directory
        else:
            abs_path = backend_dir / credentials_path
            if abs_path.exists():
                credentials_path = str(abs_path.absolute())
    
    # Set absolute path if file exists
    if os.path.exists(credentials_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(credentials_path)

# Support DB_HOST as alias for INSTANCE_CONNECTION_NAME (for backward compatibility)
if not os.getenv("INSTANCE_CONNECTION_NAME") and os.getenv("DB_HOST"):
    os.environ["INSTANCE_CONNECTION_NAME"] = os.getenv("DB_HOST")

# Support DB_PASSWORD as alias for DB_PASS (for backward compatibility)
if not os.getenv("DB_PASS") and os.getenv("DB_PASSWORD"):
    os.environ["DB_PASS"] = os.getenv("DB_PASSWORD")

# Check if database environment variables are set
DB_CONFIGURED = all([
    os.getenv("INSTANCE_CONNECTION_NAME"),
    os.getenv("DB_USER"),
    os.getenv("DB_PASS"),
    os.getenv("DB_NAME"),
    os.getenv("DB_TYPE"),
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
])


@pytest.fixture(autouse=True, scope="function")
def ensure_db_env_vars(request, monkeypatch):
    """
    Ensure database environment variables are loaded from .env for integration tests.
    This runs after mock_config, so it will restore real values if they were overridden.
    Also resets the database client singleton to ensure fresh initialization.
    """
    # Only run for tests marked with requires_db or requires_gcp
    requires_db = any(marker.name == "requires_db" for marker in request.node.iter_markers())
    requires_gcp = any(marker.name == "requires_gcp" for marker in request.node.iter_markers())
    
    if requires_db or requires_gcp:
        # Close any existing database client to force reinitialization with fresh env vars
        try:
            from database.cloud_sql_client import close_db_client, _client_instance
            # Force reset the singleton
            close_db_client()
            # Also directly reset the module-level variable
            import database.cloud_sql_client as db_module
            db_module._client_instance = None
        except Exception:
            pass  # Ignore if client doesn't exist yet
        
        # Reload .env to ensure real credentials are used
        # This ensures values from .env override any test mocks
        load_dotenv(dotenv_path=project_root / ".env", override=True)
        load_dotenv(dotenv_path=backend_dir / ".env", override=True)
        load_dotenv(override=True)
        
        # Re-resolve GOOGLE_APPLICATION_CREDENTIALS
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path:
            if credentials_path.startswith("./"):
                credentials_path = credentials_path[2:]
            
            if not os.path.isabs(credentials_path):
                abs_path = project_root / credentials_path
                if abs_path.exists():
                    credentials_path = str(abs_path.absolute())
                else:
                    abs_path = backend_dir / credentials_path
                    if abs_path.exists():
                        credentials_path = str(abs_path.absolute())
            
            if os.path.exists(credentials_path):
                abs_creds_path = os.path.abspath(credentials_path)
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_creds_path
                monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", abs_creds_path)
        
        # Re-apply aliases and set via monkeypatch to ensure they stick
        if not os.getenv("INSTANCE_CONNECTION_NAME") and os.getenv("DB_HOST"):
            instance_name = os.getenv("DB_HOST")
            os.environ["INSTANCE_CONNECTION_NAME"] = instance_name
            monkeypatch.setenv("INSTANCE_CONNECTION_NAME", instance_name)
        
        if not os.getenv("DB_PASS") and os.getenv("DB_PASSWORD"):
            db_pass = os.getenv("DB_PASSWORD")
            os.environ["DB_PASS"] = db_pass
            monkeypatch.setenv("DB_PASS", db_pass)
        
        # Set all DB env vars via monkeypatch to ensure they override any mocks
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS") or os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")
        instance_name = os.getenv("INSTANCE_CONNECTION_NAME") or os.getenv("DB_HOST")
        
        if db_user:
            monkeypatch.setenv("DB_USER", db_user)
        if db_pass:
            monkeypatch.setenv("DB_PASS", db_pass)
            monkeypatch.setenv("DB_PASSWORD", db_pass)
        if db_name:
            monkeypatch.setenv("DB_NAME", db_name)
        if instance_name:
            monkeypatch.setenv("INSTANCE_CONNECTION_NAME", instance_name)
            monkeypatch.setenv("DB_HOST", instance_name)
        
        # Verify we have real credentials, not test mocks
        final_db_user = os.getenv("DB_USER")
        if final_db_user == "test-user":
            raise ValueError(
                "DB_USER is set to 'test-user' (test mock). "
                "Integration tests require real database credentials from .env file. "
                "Please ensure your .env file has correct DB_USER, DB_PASS, DB_NAME, "
                "INSTANCE_CONNECTION_NAME, and GOOGLE_APPLICATION_CREDENTIALS set."
            )


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.requires_gcp
class TestDatabaseConnection:
    """Tests for database connection."""
    
    def test_connection(self):
        """Test basic connection to Cloud SQL."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            assert client is not None
            
            # Test connection - using synchronous SQLAlchemy API
            with client.get_connection() as conn:
                # Test basic query
                result = conn.execute(text("SELECT 1"))
                row = result.fetchone()
                assert row[0] == 1
                
                # Test database name
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.fetchone()[0]
                assert db_name is not None
                
                # Test PostgreSQL version
                result = conn.execute(text("SELECT version()"))
                pg_version = result.fetchone()[0]
                assert pg_version is not None
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()
    
    def test_table_existence(self):
        """Check if threads and messages tables exist."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            
            with client.get_connection() as conn:
                # Check threads table
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'threads'
                    )
                """))
                threads_exists = result.fetchone()[0]
                
                # Check messages table
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'messages'
                    )
                """))
                messages_exists = result.fetchone()[0]
                
                assert threads_exists is True, "Threads table should exist"
                assert messages_exists is True, "Messages table should exist"
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.requires_gcp
class TestDatabaseCRUD:
    """Tests for CRUD operations."""
    
    def test_create_thread(self):
        """Test CREATE operation (INSERT thread)."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            test_thread_id = f"test-thread-{int(datetime.now().timestamp())}"
            
            query = text("""
                INSERT INTO threads (thread_id, title, created_at, updated_at, user_id)
                VALUES (:thread_id, :title, :created_at, :updated_at, :user_id)
                RETURNING thread_id, title, created_at
            """)
            
            with client.get_connection() as conn:
                result = conn.execute(query, {
                    "thread_id": test_thread_id,
                    "title": "Test Thread for CRUD",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "user_id": "test-user"
                })
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == test_thread_id
                assert row[1] == "Test Thread for CRUD"
                
                # Cleanup
                conn.execute(text("DELETE FROM threads WHERE thread_id = :thread_id"), {
                    "thread_id": test_thread_id
                })
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()
    
    def test_read_thread(self):
        """Test READ operation (SELECT thread)."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            test_thread_id = f"test-thread-{int(datetime.now().timestamp())}"
            
            # Create a thread first
            create_query = text("""
                INSERT INTO threads (thread_id, title, created_at, updated_at, user_id)
                VALUES (:thread_id, :title, :created_at, :updated_at, :user_id)
            """)
            
            with client.get_connection() as conn:
                conn.execute(create_query, {
                    "thread_id": test_thread_id,
                    "title": "Test Thread for READ",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "user_id": "test-user"
                })
                
                # Read the thread
                read_query = text("""
                    SELECT thread_id, title, created_at, updated_at, user_id
                    FROM threads
                    WHERE thread_id = :thread_id
                """)
                
                result = conn.execute(read_query, {"thread_id": test_thread_id})
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == test_thread_id
                assert row[1] == "Test Thread for READ"
                
                # Cleanup
                conn.execute(text("DELETE FROM threads WHERE thread_id = :thread_id"), {
                    "thread_id": test_thread_id
                })
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()
    
    def test_update_thread(self):
        """Test UPDATE operation."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            test_thread_id = f"test-thread-{int(datetime.now().timestamp())}"
            new_title = f"Updated Test Thread - {datetime.now().strftime('%H:%M:%S')}"
            
            # Create a thread first
            create_query = text("""
                INSERT INTO threads (thread_id, title, created_at, updated_at, user_id)
                VALUES (:thread_id, :title, :created_at, :updated_at, :user_id)
            """)
            
            with client.get_connection() as conn:
                conn.execute(create_query, {
                    "thread_id": test_thread_id,
                    "title": "Original Title",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "user_id": "test-user"
                })
                
                # Update the thread
                update_query = text("""
                    UPDATE threads
                    SET title = :title, updated_at = :updated_at
                    WHERE thread_id = :thread_id
                    RETURNING thread_id, title, updated_at
                """)
                
                result = conn.execute(update_query, {
                    "title": new_title,
                    "updated_at": datetime.utcnow(),
                    "thread_id": test_thread_id
                })
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == test_thread_id
                assert row[1] == new_title
                
                # Cleanup
                conn.execute(text("DELETE FROM threads WHERE thread_id = :thread_id"), {
                    "thread_id": test_thread_id
                })
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()
    
    def test_delete_thread(self):
        """Test DELETE operation."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            test_thread_id = f"test-thread-{int(datetime.now().timestamp())}"
            
            # Create a thread first
            create_query = text("""
                INSERT INTO threads (thread_id, title, created_at, updated_at, user_id)
                VALUES (:thread_id, :title, :created_at, :updated_at, :user_id)
            """)
            
            with client.get_connection() as conn:
                conn.execute(create_query, {
                    "thread_id": test_thread_id,
                    "title": "Test Thread for DELETE",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "user_id": "test-user"
                })
                
                # Delete the thread
                delete_query = text("DELETE FROM threads WHERE thread_id = :thread_id RETURNING thread_id")
                result = conn.execute(delete_query, {"thread_id": test_thread_id})
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == test_thread_id
                
                # Verify deletion
                verify_query = text("SELECT COUNT(*) FROM threads WHERE thread_id = :thread_id")
                result = conn.execute(verify_query, {"thread_id": test_thread_id})
                count = result.fetchone()[0]
                
                assert count == 0, "Thread should be deleted"
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()
    
    def test_message_operations(self):
        """Test message CRUD operations."""
        if not DB_CONFIGURED:
            pytest.skip("Database environment variables not configured")
        
        from database.cloud_sql_client import get_db_client
        
        try:
            client = get_db_client()
            test_thread_id = f"test-thread-msg-{int(datetime.now().timestamp())}"
            message_id = f"test-msg-{int(datetime.now().timestamp())}"
            
            with client.get_connection() as conn:
                # Create a test thread first
                create_thread_query = text("""
                    INSERT INTO threads (thread_id, title, created_at, updated_at)
                    VALUES (:thread_id, :title, :created_at, :updated_at)
                    ON CONFLICT (thread_id) DO NOTHING
                """)
                
                conn.execute(create_thread_query, {
                    "thread_id": test_thread_id,
                    "title": "Test Thread for Messages",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
                # Create a message
                create_message_query = text("""
                    INSERT INTO messages (message_id, thread_id, role, content, timestamp)
                    VALUES (:message_id, :thread_id, :role, :content, :timestamp)
                    RETURNING message_id, thread_id, role, content
                """)
                
                result = conn.execute(create_message_query, {
                    "message_id": message_id,
                    "thread_id": test_thread_id,
                    "role": "user",
                    "content": "This is a test message",
                    "timestamp": datetime.utcnow()
                })
                row = result.fetchone()
                
                assert row is not None
                assert row[0] == message_id
                assert row[1] == test_thread_id
                assert row[2] == "user"
                assert row[3] == "This is a test message"
                
                # Read messages for thread
                read_messages_query = text("""
                    SELECT message_id, role, content, timestamp
                    FROM messages
                    WHERE thread_id = :thread_id
                    ORDER BY timestamp ASC
                """)
                
                result = conn.execute(read_messages_query, {"thread_id": test_thread_id})
                messages = result.fetchall()
                assert len(messages) > 0
                
                # Cleanup
                conn.execute(text("DELETE FROM messages WHERE message_id = :message_id"), {
                    "message_id": message_id
                })
                conn.execute(text("DELETE FROM threads WHERE thread_id = :thread_id"), {
                    "thread_id": test_thread_id
                })
        finally:
            from database.cloud_sql_client import close_db_client
            close_db_client()

