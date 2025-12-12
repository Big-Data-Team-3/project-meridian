"""
Comprehensive test script for Cloud SQL client.
Tests connection, CRUD operations, and verifies all functionality.
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path (project root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import using the same approach as test_connection.py
# Add meridian-backend to path for direct import
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.cloud_sql_client import get_db_client, close_db_client


async def test_connection():
    """Test basic connection to Cloud SQL."""
    print("=" * 60)
    print("TEST 1: Basic Connection Test")
    print("=" * 60)
    
    try:
        client = get_db_client()
        print("✅ Cloud SQL client initialized")
        
        # Test connection
        async with client.get_connection() as conn:
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            print(f"✅ Connection successful: SELECT 1 = {result}")
            
            # Test database name
            db_name = await conn.fetchval("SELECT current_database()")
            print(f"✅ Connected to database: {db_name}")
            
            # Test PostgreSQL version
            pg_version = await conn.fetchval("SELECT version()")
            print(f"✅ PostgreSQL version: {pg_version.split(',')[0]}")
        
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_table_exists():
    """Check if threads and messages tables exist."""
    print("\n" + "=" * 60)
    print("TEST 2: Table Existence Check")
    print("=" * 60)
    
    try:
        client = get_db_client()
        
        async with client.get_connection() as conn:
            # Check threads table
            threads_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'threads'
                )
            """)
            
            # Check messages table
            messages_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'messages'
                )
            """)
            
            print(f"✅ Threads table exists: {threads_exists}")
            print(f"✅ Messages table exists: {messages_exists}")
            
            if not threads_exists or not messages_exists:
                print("\n⚠️  Warning: Tables don't exist. Run migrations first:")
                print("   python meridian-backend/database/run_migrations.py")
                return False
            
            return True
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_create_operation():
    """Test CREATE operation (INSERT)."""
    print("\n" + "=" * 60)
    print("TEST 3: CREATE Operation (INSERT)")
    print("=" * 60)
    
    try:
        client = get_db_client()
        test_thread_id = f"test-thread-{int(datetime.now().timestamp())}"
        
        # Insert a test thread
        query = """
            INSERT INTO threads (thread_id, title, created_at, updated_at, user_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING thread_id, title, created_at
        """
        
        async with client.get_connection() as conn:
            row = await conn.fetchrow(
                query,
                test_thread_id,
                "Test Thread for CRUD",
                datetime.utcnow(),
                datetime.utcnow(),
                "test-user"
            )
            
            print(f"✅ Thread created successfully:")
            print(f"   Thread ID: {row['thread_id']}")
            print(f"   Title: {row['title']}")
            print(f"   Created: {row['created_at']}")
        
        return test_thread_id
    except Exception as e:
        print(f"❌ CREATE operation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_read_operation(thread_id: str):
    """Test READ operation (SELECT)."""
    print("\n" + "=" * 60)
    print("TEST 4: READ Operation (SELECT)")
    print("=" * 60)
    
    if not thread_id:
        print("⚠️  Skipping READ test - no thread ID from CREATE test")
        return False
    
    try:
        client = get_db_client()
        
        # Read the thread we just created
        query = """
            SELECT thread_id, title, created_at, updated_at, user_id
            FROM threads
            WHERE thread_id = $1
        """
        
        async with client.get_connection() as conn:
            row = await conn.fetchrow(query, thread_id)
            
            if row:
                print(f"✅ Thread retrieved successfully:")
                print(f"   Thread ID: {row['thread_id']}")
                print(f"   Title: {row['title']}")
                print(f"   Created: {row['created_at']}")
                print(f"   Updated: {row['updated_at']}")
                print(f"   User ID: {row['user_id']}")
                return True
            else:
                print(f"❌ Thread not found: {thread_id}")
                return False
    except Exception as e:
        print(f"❌ READ operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_update_operation(thread_id: str):
    """Test UPDATE operation."""
    print("\n" + "=" * 60)
    print("TEST 5: UPDATE Operation")
    print("=" * 60)
    
    if not thread_id:
        print("⚠️  Skipping UPDATE test - no thread ID from CREATE test")
        return False
    
    try:
        client = get_db_client()
        new_title = f"Updated Test Thread - {datetime.now().strftime('%H:%M:%S')}"
        
        # Update the thread
        query = """
            UPDATE threads
            SET title = $1, updated_at = $2
            WHERE thread_id = $3
            RETURNING thread_id, title, updated_at
        """
        
        async with client.get_connection() as conn:
            row = await conn.fetchrow(
                query,
                new_title,
                datetime.utcnow(),
                thread_id
            )
            
            if row:
                print(f"✅ Thread updated successfully:")
                print(f"   Thread ID: {row['thread_id']}")
                print(f"   New Title: {row['title']}")
                print(f"   Updated At: {row['updated_at']}")
                return True
            else:
                print(f"❌ Thread not found for update: {thread_id}")
                return False
    except Exception as e:
        print(f"❌ UPDATE operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_delete_operation(thread_id: str):
    """Test DELETE operation."""
    print("\n" + "=" * 60)
    print("TEST 6: DELETE Operation")
    print("=" * 60)
    
    if not thread_id:
        print("⚠️  Skipping DELETE test - no thread ID from CREATE test")
        return False
    
    try:
        client = get_db_client()
        
        # Delete the thread
        query = "DELETE FROM threads WHERE thread_id = $1 RETURNING thread_id"
        
        async with client.get_connection() as conn:
            row = await conn.fetchrow(query, thread_id)
            
            if row:
                print(f"✅ Thread deleted successfully:")
                print(f"   Deleted Thread ID: {row['thread_id']}")
                
                # Verify deletion
                verify_query = "SELECT COUNT(*) FROM threads WHERE thread_id = $1"
                count = await conn.fetchval(verify_query, thread_id)
                
                if count == 0:
                    print(f"✅ Deletion verified: Thread no longer exists")
                    return True
                else:
                    print(f"❌ Deletion verification failed: Thread still exists")
                    return False
            else:
                print(f"❌ Thread not found for deletion: {thread_id}")
                return False
    except Exception as e:
        print(f"❌ DELETE operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_message_operations(thread_id: str):
    """Test message CRUD operations."""
    print("\n" + "=" * 60)
    print("TEST 7: Message Operations")
    print("=" * 60)
    
    if not thread_id:
        print("⚠️  Skipping message test - no thread ID")
        return False
    
    try:
        client = get_db_client()
        
        # Create a test thread first (since we might have deleted it)
        create_thread_query = """
            INSERT INTO threads (thread_id, title, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (thread_id) DO NOTHING
        """
        
        async with client.get_connection() as conn:
            await conn.execute(
                create_thread_query,
                thread_id,
                "Test Thread for Messages",
                datetime.utcnow(),
                datetime.utcnow()
            )
            
            # Create a message
            message_id = f"test-msg-{int(datetime.now().timestamp())}"
            create_message_query = """
                INSERT INTO messages (message_id, thread_id, role, content, timestamp)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING message_id, thread_id, role, content
            """
            
            row = await conn.fetchrow(
                create_message_query,
                message_id,
                thread_id,
                "user",
                "This is a test message",
                datetime.utcnow()
            )
            
            print(f"✅ Message created:")
            print(f"   Message ID: {row['message_id']}")
            print(f"   Thread ID: {row['thread_id']}")
            print(f"   Role: {row['role']}")
            print(f"   Content: {row['content']}")
            
            # Read messages for thread
            read_messages_query = """
                SELECT message_id, role, content, timestamp
                FROM messages
                WHERE thread_id = $1
                ORDER BY timestamp ASC
            """
            
            messages = await conn.fetch(read_messages_query, thread_id)
            print(f"✅ Retrieved {len(messages)} message(s) for thread")
            
            # Cleanup
            await conn.execute("DELETE FROM messages WHERE message_id = $1", message_id)
            await conn.execute("DELETE FROM threads WHERE thread_id = $1", thread_id)
            print(f"✅ Cleaned up test data")
            
            return True
    except Exception as e:
        print(f"❌ Message operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "🔍 " * 30)
    print("CLOUD SQL CLIENT COMPREHENSIVE TEST SUITE")
    print("🔍 " * 30 + "\n")
    
    # Check environment variables
    print("=" * 60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)
    
    required_vars = {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_NAME": os.getenv("DB_NAME"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    }
    
    missing = []
    for var, value in required_vars.items():
        if value:
            if var == "DB_PASSWORD":
                print(f"✅ {var}: {'*' * min(len(value), 10)}")
            elif var == "GOOGLE_APPLICATION_CREDENTIALS":
                exists = os.path.exists(value) if value else False
                status = "✅" if exists else "❌"
                print(f"{status} {var}: {value} {'(file exists)' if exists else '(file NOT found)'}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\n❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set them before running tests:")
        print("  export DB_HOST='project:region:instance'")
        print("  export DB_USER='your_db_user'")
        print("  export DB_PASSWORD='your_db_password'")
        print("  export DB_NAME='your_db_name'")
        print("  export GOOGLE_APPLICATION_CREDENTIALS='/path/to/service-account.json'")
        return False
    
    print("\n✅ All required environment variables are set\n")
    
    # Run tests
    results = []
    
    # Test 1: Connection
    results.append(("Connection", await test_connection()))
    
    # Test 2: Table existence
    results.append(("Table Existence", await test_table_exists()))
    
    # Test 3: CREATE
    thread_id = await test_create_operation()
    results.append(("CREATE", thread_id is not None))
    
    # Test 4: READ
    results.append(("READ", await test_read_operation(thread_id)))
    
    # Test 5: UPDATE
    results.append(("UPDATE", await test_update_operation(thread_id)))
    
    # Test 6: DELETE
    results.append(("DELETE", await test_delete_operation(thread_id)))
    
    # Test 7: Messages (create new thread for this)
    test_thread_id = f"test-thread-msg-{int(datetime.now().timestamp())}"
    results.append(("Messages", await test_message_operations(test_thread_id)))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'=' * 60}")
    print(f"Total: {passed}/{total} tests passed")
    print(f"{'=' * 60}\n")
    
    if passed == total:
        print("🎉 All tests passed! Cloud SQL client is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        try:
            asyncio.run(close_db_client())
        except:
            pass

