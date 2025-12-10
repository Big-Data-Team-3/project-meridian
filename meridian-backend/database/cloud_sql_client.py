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
load_dotenv()


class CloudSQLClient:
    """
    Cloud SQL client for managing database connections.
    Wraps the existing connect_with_connector logic in a class structure.
    """
    
    def __init__(self):
        """
        Initialize the Cloud SQL client.
        Loads environment variables and prepares for connection.
        """
        self.instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
        self.db_user = os.environ.get("DB_USER")
        self.db_pass = os.environ.get("DB_PASS")
        self.db_name = os.environ.get("DB_NAME")
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

        instance_connection_name = self.instance_connection_name or os.environ[
            "INSTANCE_CONNECTION_NAME"
        ]  # e.g. 'project:region:instance'
        db_user = self.db_user or os.environ["DB_USER"]  # e.g. 'my-db-user'
        db_pass = self.db_pass or os.environ["DB_PASS"]  # e.g. 'my-db-password'
        db_name = self.db_name or os.environ["DB_NAME"]  # e.g. 'my-database'

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
