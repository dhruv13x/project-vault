import os
import boto3
from botocore.exceptions import ClientError

def get_client(endpoint_url: str, aws_access_key_id: str, aws_secret_access_key: str):
    """
    Initializes and returns a boto3 S3 client.

    Args:
        endpoint_url: The endpoint URL (e.g., for Backblaze B2).
        aws_access_key_id: The AWS Access Key ID.
        aws_secret_access_key: The AWS Secret Access Key.

    Returns:
        A boto3 client object for S3.
    """
    return boto3.client(
        service_name='s3',
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

def upload_file(client, bucket_name: str, local_path: str, object_name: str):
    """
    Uploads a file to an S3 bucket.

    Args:
        client: The boto3 S3 client.
        bucket_name: The name of the bucket.
        local_path: The local path to the file to upload.
        object_name: The key (path) in the bucket.
    """
    print(f"Uploading {local_path} to s3://{bucket_name}/{object_name}...")
    try:
        client.upload_file(local_path, bucket_name, object_name)
    except ClientError as e:
        print(f"Error uploading {local_path}: {e}")
        raise

def list_existing_objects(client, bucket_name: str, prefix: str) -> set:
    """
    Lists all objects in a bucket with a given prefix.

    Args:
        client: The boto3 S3 client.
        bucket_name: The name of the bucket.
        prefix: The prefix to filter objects by.

    Returns:
        A set of object keys (strings) found in the bucket.
    """
    existing_objects = set()
    paginator = client.get_paginator('list_objects_v2')
    
    try:
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    existing_objects.add(obj['Key'])
    except ClientError as e:
        print(f"Error listing objects: {e}")
        raise
        
    return existing_objects
