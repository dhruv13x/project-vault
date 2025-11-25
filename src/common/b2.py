# src/common/b2.py

from b2sdk.v2 import InMemoryAccountInfo, B2Api
from typing import Set
import os

class B2Manager:
    def __init__(self, key_id: str, app_key: str, bucket_name: str):
        info = InMemoryAccountInfo()
        self.api = B2Api(info)
        self.api.authorize_account("production", key_id, app_key)
        self.bucket = self.api.get_bucket_by_name(bucket_name)

    def upload_file(self, local_path: str, remote_name: str):
        """
        Uploads a local file to B2.
        """
        print(f"Uploading {local_path} -> {remote_name}")
        self.bucket.upload_local_file(local_file=local_path, file_name=remote_name)

    def download_file(self, remote_name: str, local_path: str):
        """
        Downloads a file from B2 to the local path.
        """
        print(f"Downloading {remote_name} -> {local_path}")
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            downloaded_file = self.bucket.download_file_by_name(remote_name)
            downloaded_file.save_to(local_path)
        except Exception as e:
            print(f"Error downloading {remote_name}: {e}")
            raise

    def list_file_names(self) -> Set[str]:
        """
        Lists all file names in the bucket recursively.
        Returns a set of strings for O(1) lookup.
        """
        file_names = set()
        # bucket.ls returns a generator yielding (FileVersion, folder_name)
        for file_version, _ in self.bucket.ls(recursive=True):
            file_names.add(file_version.file_name)
        return file_names
