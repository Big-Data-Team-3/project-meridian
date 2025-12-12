"""
Cloud SQL client for managing database connections to GCP Cloud SQL.
Wraps the existing connect_with_connector logic in a class structure.
"""
import os
from typing import Optional

from google.cloud.sql.connector import Connector, IPTypes
import pg8000

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine.base import Engine

from dotenv import load_dotenv


class CloudSQLClient:
    """
    Cloud SQL client for managing database connections.
    Wraps the existing connect_with_connector logic in a class structure.
    """
    
    def __init__(self):
        """
        Initialize the Cloud SQL client.
        Loads environment variables and prepares for connection.
        
        Raises:
            ValueError: If required environment variables are not set
        """
        # Determine if we're in Cloud Run
        is_cloud_run = bool(os.environ.get("K_SERVICE"))
        
        # Only load .env file in local development (not in Cloud Run)
        # In Cloud Run, environment variables are set directly by the deployment script
        if not is_cloud_run and os.environ.get("ENVIRONMENT") != "production":
            load_dotenv()
        
        # Determine database name based on environment
        # Priority: 
        #   - Cloud Run: Use DB_NAME set by deployment script (or PROD_DB_NAME as fallback)
        #   - Local Dev: Prioritize DEV_DB_NAME over DB_NAME from .env (to avoid conflicts)
        if is_cloud_run:
            # In Cloud Run, use DB_NAME set by deployment script (or PROD_DB_NAME as fallback)
            db_name = os.environ.get("DB_NAME") or os.environ.get("PROD_DB_NAME", "meridian_prod")
        else:
            # In local dev, prioritize DEV_DB_NAME over DB_NAME from .env
            # This prevents .env DB_NAME='meridian_prod' from overriding DEV_DB_NAME='postgres'
            db_name = os.environ.get("DEV_DB_NAME") or os.environ.get("DB_NAME", "meridian_dev")
            # Set it in environment so subsequent code uses the correct value
            os.environ["DB_NAME"] = db_name
        
        # Validate required environment variables at initialization time
        # Note: In Cloud Run, these are set directly as environment variables
        # In local dev, they may come from .env file (loaded above if not in production)
        required_vars = {
            "INSTANCE_CONNECTION_NAME": os.environ.get("INSTANCE_CONNECTION_NAME"),
            "DB_USER": os.environ.get("DB_USER"),
            "DB_PASS": os.environ.get("DB_PASS"),  # Note: Cloud uses DB_PASS, not DB_PASSWORD
            "DB_NAME": db_name,  # Use the determined database name
        }
        
        # Provide helpful error message if using wrong variable names
        if not required_vars["INSTANCE_CONNECTION_NAME"] and os.environ.get("DB_HOST"):
            raise ValueError(
                "Found DB_HOST but need INSTANCE_CONNECTION_NAME. "
                "Please use INSTANCE_CONNECTION_NAME (format: project:region:instance)"
            )
        if not required_vars["DB_PASS"] and os.environ.get("DB_PASSWORD"):
            raise ValueError(
                "Found DB_PASSWORD but need DB_PASS. "
                "Please use DB_PASS for consistency with Cloud Run deployment"
            )
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please set them in your environment or .env file."
            )
        
        self.instance_connection_name = required_vars["INSTANCE_CONNECTION_NAME"]
        self.db_user = required_vars["DB_USER"]
        self.db_pass = required_vars["DB_PASS"]
        self.db_name = required_vars["DB_NAME"]
        self.pool: Optional[Engine] = None
        self.connector: Optional[Connector] = None

    def connect_with_connector(self) -> Engine:
        """
        Initializes a connection pool for a Cloud SQL instance of Postgres.

        Uses the Cloud SQL Python Connector package.
        
        NOTE: This method preserves the EXACT logic from the original function.
        DO NOT modify the core connection logic.
        
        Returns:
            SQLAlchemy Engine instance for database connections
        """
        # Note: Saving credentials in environment variables is convenient, but not
        # secure - consider a more secure solution such as
        # Cloud Secret Manager (https://cloud.google.com/secret-manager) to help
        # keep secrets safe.

        # Use instance variables (already validated in __init__)
        # Fallback to environment variables only if instance variables are None
        # (shouldn't happen after validation, but kept for safety)
        instance_connection_name = self.instance_connection_name or os.environ.get(
            "INSTANCE_CONNECTION_NAME"
        )  # e.g. 'project:region:instance'
        db_user = self.db_user or os.environ.get("DB_USER")  # e.g. 'my-db-user'
        db_pass = self.db_pass or os.environ.get("DB_PASS")  # e.g. 'my-db-password'
        db_name = self.db_name or os.environ.get("DB_NAME")  # e.g. 'my-database'
        
        # Final validation before connection attempt
        if not all([instance_connection_name, db_user, db_pass, db_name]):
            missing = []
            if not instance_connection_name:
                missing.append("INSTANCE_CONNECTION_NAME")
            if not db_user:
                missing.append("DB_USER")
            if not db_pass:
                missing.append("DB_PASS")
            if not db_name:
                missing.append("DB_NAME")
            raise ValueError(
                f"Missing required database configuration: {', '.join(missing)}. "
                f"Cannot establish database connection."
            )

        ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC

        # initialize Cloud SQL Python Connector object
        self.connector = Connector(refresh_strategy="LAZY")

        def getconn() -> pg8000.dbapi.Connection:
            conn: pg8000.dbapi.Connection = self.connector.connect(
                instance_connection_name,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name,
                ip_type=ip_type,
            )
            return conn

        # The Cloud SQL Python Connector can be used with SQLAlchemy
        # using the 'creator' argument to 'create_engine'
        self.pool = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            # ...
        )
        return self.pool
    
    def get_connection(self):
        """
        Get a connection from the pool.
        Initializes the pool if it hasn't been created yet.
        
        Returns:
            Connection context manager from SQLAlchemy engine
        """
        if self.pool is None:
            self.connect_with_connector()
        return self.pool.connect()
    
    def execute_query(self, query: str, params: Optional[dict] = None):
        """
        Execute a parameterized query using text() wrapper for SQLAlchemy 2.0+.
        
        Args:
            query: SQL query string
            params: Optional dictionary of parameters for the query
        
        Returns:
            Query result from SQLAlchemy
        """
        with self.get_connection() as conn:
            return conn.execute(text(query), params or {})
    
    def close(self):
        """
        Close the connection pool and cleanup resources.
        """
        if self.pool:
            self.pool.dispose()
        if self.connector:
            # Connector cleanup if needed
            pass


# Global client instance (singleton pattern)
_client_instance: Optional[CloudSQLClient] = None


def get_db_client() -> CloudSQLClient:
    """
    Get or create a CloudSQLClient instance (singleton pattern).
    
    Returns:
        CloudSQLClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = CloudSQLClient()
    return _client_instance


def close_db_client():
    """
    Close the global database client instance.
    """
    global _client_instance
    if _client_instance:
        _client_instance.close()
        _client_instance = None


if __name__ == "__main__":
    # Test the CloudSQLClient class
    client = CloudSQLClient()
    pool = client.connect_with_connector()
    with pool.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(result.fetchone())
    client.close()
