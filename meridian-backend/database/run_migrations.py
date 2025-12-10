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
        with client.get_connection() as conn:
            for migration_file in migration_files:
                print(f"\nRunning migration: {migration_file.name}")
                
                # Read migration SQL
                with open(migration_file, 'r') as f:
                    sql = f.read()
                
                # Execute migration
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Migration {migration_file.name} completed successfully")
                except Exception as e:
                    # Check if error is due to table already existing
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"⚠️  Migration {migration_file.name} skipped (already applied): {e}")
                    else:
                        print(f"❌ Migration {migration_file.name} failed: {e}")
                        raise
        
        print("\n✅ All migrations completed successfully!")
        
        # Verify tables exist
        with client.get_connection() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('threads', 'messages')
            """))
            tables = [row[0] for row in result]
            print(f"\n✅ Verified tables exist: {tables}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        close_db_client()


if __name__ == "__main__":
    run_migrations()
