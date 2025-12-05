import os
from typing import Optional, BinaryIO
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

# GCP Configuration
PROJECT_ID = os.environ.get('PROJECT_ID')
SERVICE_ACCOUNT_KEY_PATH = 'config/cloud-run-sa.json'

class GCSClient:
    """Google Cloud Storage Client for file operations."""
    
    def __init__(self, project_id: str = None, credentials_path: str = None):
        """
        Initialize GCS client.
        
        Args:
            project_id: GCP project ID (optional if set in env)
            credentials_path: Path to service account key (optional if set in env)
        """
        self.project_id = project_id or PROJECT_ID
        self.credentials_path = credentials_path or SERVICE_ACCOUNT_KEY_PATH
        
        if not self.project_id:
            raise ValueError("PROJECT_ID must be set in environment or passed to constructor")
        
        # Initialize client
        if self.credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path
            )
            self.client = storage.Client(project=self.project_id, credentials=credentials)
        else:
            # Use Application Default Credentials (ADC)
            self.client = storage.Client(project=self.project_id)
    
    def upload_file(
        self, 
        bucket_name: str, 
        source_file_path: str, 
        destination_blob_name: str,
        content_type: str = None
    ) -> str:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            source_file_path: Local path to the file to upload
            destination_blob_name: Name/path of the file in GCS
            content_type: MIME type of the file (auto-detected if None)
        
        Returns:
            str: Public URL of the uploaded file
        
        Raises:
            FileNotFoundError: If source file doesn't exist
            Exception: For other GCS errors
        """
        if not os.path.exists(source_file_path):
            raise FileNotFoundError(f"Source file not found: {source_file_path}")
        
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            # Auto-detect content type if not provided
            if content_type is None:
                content_type = self._get_content_type(source_file_path)
            
            # Upload the file
            blob.upload_from_filename(source_file_path, content_type=content_type)
            
            # Make the file publicly accessible (optional)
            blob.make_public()
            
            return blob.public_url
            
        except Exception as e:
            raise Exception(f"Failed to upload file to GCS: {str(e)}")
    
    def upload_bytes(
        self, 
        bucket_name: str, 
        data: bytes, 
        destination_blob_name: str,
        content_type: str = 'application/octet-stream'
    ) -> str:
        """
        Upload bytes/data to Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            data: Bytes to upload
            destination_blob_name: Name/path of the file in GCS
            content_type: MIME type of the data
        
        Returns:
            str: Public URL of the uploaded file
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            blob.upload_from_string(data, content_type=content_type)
            blob.make_public()
            
            return blob.public_url
            
        except Exception as e:
            raise Exception(f"Failed to upload bytes to GCS: {str(e)}")
    
    def download_file(
        self, 
        bucket_name: str, 
        source_blob_name: str, 
        destination_file_path: str
    ) -> str:
        """
        Download a file from Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            source_blob_name: Name/path of the file in GCS
            destination_file_path: Local path where to save the file
        
        Returns:
            str: Path to the downloaded file
        
        Raises:
            Exception: For GCS errors
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(source_blob_name)
            
            # Create destination directory if it doesn't exist
            dest_dir = os.path.dirname(destination_file_path)
            if dest_dir:  # Only create directory if path is not empty
                os.makedirs(dest_dir, exist_ok=True)
            
            # Download the file
            blob.download_to_filename(destination_file_path)
            
            return destination_file_path
            
        except Exception as e:
            raise Exception(f"Failed to download file from GCS: {str(e)}")
    
    def download_bytes(
        self, 
        bucket_name: str, 
        source_blob_name: str
    ) -> bytes:
        """
        Download a file from Google Cloud Storage as bytes.
        
        Args:
            bucket_name: Name of the GCS bucket
            source_blob_name: Name/path of the file in GCS
        
        Returns:
            bytes: File content as bytes
        
        Raises:
            Exception: For GCS errors
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(source_blob_name)
            
            return blob.download_as_bytes()
            
        except Exception as e:
            raise Exception(f"Failed to download bytes from GCS: {str(e)}")
    
    def list_files(
        self, 
        bucket_name: str, 
        prefix: str = None,
        max_results: int = None
    ) -> list:
        """
        List files in a GCS bucket.
        
        Args:
            bucket_name: Name of the GCS bucket
            prefix: Filter files by prefix (e.g., 'folder/')
            max_results: Maximum number of results to return
        
        Returns:
            list: List of blob names
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix, max_results=max_results)
            
            return [blob.name for blob in blobs]
            
        except Exception as e:
            raise Exception(f"Failed to list files in GCS: {str(e)}")
    
    def delete_file(self, bucket_name: str, blob_name: str) -> bool:
        """
        Delete a file from Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            blob_name: Name/path of the file in GCS
        
        Returns:
            bool: True if deleted successfully
        
        Raises:
            Exception: For GCS errors
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            blob.delete()
            return True
            
        except Exception as e:
            raise Exception(f"Failed to delete file from GCS: {str(e)}")
    
    def file_exists(self, bucket_name: str, blob_name: str) -> bool:
        """
        Check if a file exists in Google Cloud Storage.
        
        Args:
            bucket_name: Name of the GCS bucket
            blob_name: Name/path of the file in GCS
        
        Returns:
            bool: True if file exists
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            return blob.exists()
            
        except Exception as e:
            return False
    
    def _get_content_type(self, file_path: str) -> str:
        """
        Get MIME content type for a file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            str: MIME content type
        """
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'


# Convenience functions for direct use
def create_gcs_client(project_id: str = None, credentials_path: str = None) -> GCSClient:
    """Create and return a GCS client instance."""
    return GCSClient(project_id, credentials_path)

def upload_file_to_gcs(
    bucket_name: str, 
    source_file_path: str, 
    destination_blob_name: str,
    project_id: str = None,
    credentials_path: str = None
) -> str:
    """
    Convenience function to upload a file to GCS.
    
    Returns:
        str: Public URL of the uploaded file
    """
    client = GCSClient(project_id, credentials_path)
    return client.upload_file(bucket_name, source_file_path, destination_blob_name)

def download_file_from_gcs(
    bucket_name: str, 
    source_blob_name: str, 
    destination_file_path: str,
    project_id: str = None,
    credentials_path: str = None
) -> str:
    """
    Convenience function to download a file from GCS.
    
    Returns:
        str: Path to the downloaded file
    """
    client = GCSClient(project_id, credentials_path)
    return client.download_file(bucket_name, source_blob_name, destination_file_path)

def delete_file_from_gcs(
    bucket_name: str,
    source_blob_name: str,
    project_id: str = None,
    credentials_path: str = None
) -> bool:
    """
    Convenience function to delete a file from GCS.
    """
    client = GCSClient(project_id, credentials_path)
    return client.delete_file(bucket_name, source_blob_name)

if __name__ == "__main__":
    print("=" * 70)
    with open("test.txt", "w") as f:
        f.write("Hello, GCS!\nThis is a test file.")
    print("Testing Upload/Download of a file to GCS...")
    print("-" * 70)
    print("Uploading file to GCS...")
    upload_file_to_gcs("meridian-raw-data", "test.txt", "test.txt")
    print("File uploaded to GCS...")
    print("-" * 70)
    print("Downloading file from GCS...")
    download_file_from_gcs("meridian-raw-data", "test.txt", "test.txt")
    print("File downloaded from GCS...")
    print("-" * 70)
    print("Deleting file from GCS...")
    delete_file_from_gcs("meridian-raw-data", "test.txt")
    print("File deleted from GCS...")
    import os
    if os.path.exists("test.txt"):
        os.remove("test.txt")
        print("Local file 'test.txt' deleted.")
    else:
        print("Local file 'test.txt' does not exist.")
    print("-" * 70)
    print("Completed testing Upload/Download of a file to GCS...")
    print("=" * 70)