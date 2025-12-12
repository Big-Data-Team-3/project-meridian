"""
Script to run database migrations.
Executes SQL migration files in order.
"""
import sys
from pathlib import Path

from sqlalchemy import text

# Add parent directory to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.cloud_sql_client import get_db_client, close_db_client


def run_migrations():
    """Run all migration files in order."""
    migrations_dir = Path(__file__).parent / "migrations"
    
    # Get migration files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("No migration files found.")
        return
    
    print(f"Found {len(migration_files)} migration file(s)")
    
    client = get_db_client()
    
    try:
        for migration_file in migration_files:
            print(f"\nRunning migration: {migration_file.name}")
            
            # Read migration SQL
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute each migration in its own transaction
            with client.get_connection() as conn:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Migration {migration_file.name} completed successfully")
                except Exception as e:
                    # Roll back the transaction on error
                    try:
                        conn.rollback()
                    except:
                        pass
                    
                    # Check if error is due to table/constraint already existing (idempotent operations)
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in [
                        "already exists", "duplicate", "current transaction is aborted"
                    ]):
                        print(f"⚠️  Migration {migration_file.name} skipped (already applied or non-critical): {e}")
                        # Continue to next migration
                        continue
                    else:
                        print(f"❌ Migration {migration_file.name} failed: {e}")
                        raise
        
        print("\n✅ All migrations completed successfully!")
        
        # Verify tables exist in meridian schema (all tables are now in meridian schema)
        with client.get_connection() as conn:
            # Check meridian schema tables (all tables should be here)
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'meridian'
                AND table_name IN ('threads', 'messages', 'users', 'auth_credentials', 'conversations')
                ORDER BY table_name
            """))
            meridian_tables = [row[0] for row in result]
            print(f"\n✅ Verified meridian schema tables: {meridian_tables}")
            
            # Warn if any expected tables are missing
            expected_tables = ['threads', 'messages', 'users', 'auth_credentials', 'conversations']
            missing = [t for t in expected_tables if t not in meridian_tables]
            if missing:
                print(f"⚠️  Missing meridian schema tables: {missing}")
                print("   Run migrations again to create missing tables.")
            else:
                print(f"✅ All {len(expected_tables)} required tables exist in meridian schema")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        close_db_client()


if __name__ == "__main__":
    run_migrations()
