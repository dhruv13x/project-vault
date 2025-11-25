# src/common/s3.py

import os
import boto3
from botocore.exceptions import ClientError
from typing import Set

class S3Manager:
    def __init__(self, key_id: str, secret_key: str, bucket_name: str, endpoint_url: str = None):
        """
        Initializes the S3 Manager.
        
        Args:
            key_id: AWS Access Key ID.
            secret_key: AWS Secret Access Key.
            bucket_name: The name of the bucket.
            endpoint_url: Optional S3 endpoint URL (e.g., for MinIO or B2 S3-compatible).
        """
        self.bucket_name = bucket_name
        self.client = boto3.client(
            service_name='s3',
            endpoint_url=endpoint_url,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret_key
        )

    def upload_file(self, local_path: str, remote_name: str):
        """
        Uploads a local file to the S3 bucket.
        """
        print(f"Uploading {local_path} -> s3://{self.bucket_name}/{remote_name}")
        try:
            self.client.upload_file(local_path, self.bucket_name, remote_name)
        except ClientError as e:
            print(f"Error uploading {local_path}: {e}")
            raise

    def download_file(self, remote_name: str, local_path: str):
        """
        Downloads a file from S3 to the local path.
        """
        print(f"Downloading s3://{self.bucket_name}/{remote_name} -> {local_path}")
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.download_file(self.bucket_name, remote_name, local_path)
        except ClientError as e:
            print(f"Error downloading {remote_name}: {e}")
            raise

    def list_file_names(self) -> Set[str]:
        """
        Lists all object keys in the bucket recursively.
        Returns a set of strings for O(1) lookup.
        """
        existing_objects = set()
        paginator = self.client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        existing_objects.add(obj['Key'])
        except ClientError as e:
            print(f"Error listing objects: {e}")
            raise
            
        return existing_objects
