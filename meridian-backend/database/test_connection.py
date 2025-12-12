"""
Test script to verify Cloud SQL connection and basic operations.
Run this to verify the database client works before proceeding with implementation.
"""
import os
import sys
from pathlib import Path

from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.cloud_sql_client import get_db_client, close_db_client


def test_connection():
    """Test Cloud SQL connection and basic operations."""
    print("Testing Cloud SQL connection...")
    
    try:
        client = get_db_client()
        print("✅ Cloud SQL client initialized")
        
        # Test connection
        with client.get_connection() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1"))
            row = result.fetchone()
            print(f"✅ Connection successful: SELECT 1 = {row[0]}")
            
            # Test database name
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            print(f"✅ Connected to database: {db_name}")
            
            # Check if tables exist
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            result = conn.execute(tables_query)
            tables = [row[0] for row in result]
            print(f"✅ Found {len(tables)} tables in database")
            for table in tables:
                print(f"   - {table}")
        
        print("\n✅ All connection tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        close_db_client()


if __name__ == "__main__":
    # Check environment variables
    required_vars = ["INSTANCE_CONNECTION_NAME", "DB_USER", "DB_PASS", "DB_NAME"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please set them before running this test.")
        sys.exit(1)
    
    success = test_connection()
    sys.exit(0 if success else 1)
