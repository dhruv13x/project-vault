# tests/test_common_b2.py

import os
import pytest
from unittest.mock import patch, MagicMock, Mock
from src.common.b2 import B2Manager

@pytest.fixture
def mock_b2_api():
    with patch("src.common.b2.B2Api") as mock_api:
        yield mock_api

@pytest.fixture
def mock_in_memory_account_info():
    with patch("src.common.b2.InMemoryAccountInfo") as mock_info:
        yield mock_info

@pytest.fixture
def b2_manager(mock_b2_api, mock_in_memory_account_info):
    mock_bucket = Mock()
    mock_b2_api.return_value.get_bucket_by_name.return_value = mock_bucket
    return B2Manager("id", "key", "bucket"), mock_bucket, mock_b2_api

def test_init(b2_manager):
    manager, mock_bucket, mock_api = b2_manager
    mock_api.return_value.authorize_account.assert_called_once_with("production", "id", "key")
    mock_api.return_value.get_bucket_by_name.assert_called_once_with("bucket")
    assert manager.bucket == mock_bucket

def test_upload_file(b2_manager):
    manager, mock_bucket, _ = b2_manager
    local_path = "/path/to/file.txt"
    remote_name = "remote/file.txt"

    manager.upload_file(local_path, remote_name)

    mock_bucket.upload_local_file.assert_called_once_with(local_file=local_path, file_name=remote_name)

def test_download_file(b2_manager):
    manager, mock_bucket, _ = b2_manager
    remote_name = "remote/file.txt"
    local_path = "/path/to/file.txt"

    mock_downloaded_file = Mock()
    mock_bucket.download_file_by_name.return_value = mock_downloaded_file

    with patch("os.makedirs") as mock_makedirs:
        manager.download_file(remote_name, local_path)

        mock_makedirs.assert_called_once_with("/path/to", exist_ok=True)
        mock_bucket.download_file_by_name.assert_called_once_with(remote_name)
        mock_downloaded_file.save_to.assert_called_once_with(local_path)

def test_download_file_error(b2_manager):
    manager, mock_bucket, _ = b2_manager
    remote_name = "remote/file.txt"
    local_path = "/path/to/file.txt"

    mock_bucket.download_file_by_name.side_effect = Exception("Download failed")

    with patch("os.makedirs"):
        with pytest.raises(Exception, match="Download failed"):
            manager.download_file(remote_name, local_path)

def test_list_file_names(b2_manager):
    manager, mock_bucket, _ = b2_manager

    # Mock generator yielding (FileVersion, folder_name)
    file_ver1 = Mock()
    file_ver1.file_name = "file1.txt"
    file_ver2 = Mock()
    file_ver2.file_name = "folder/file2.txt"

    mock_bucket.ls.return_value = [
        (file_ver1, None),
        (file_ver2, None)
    ]

    file_names = manager.list_file_names()

    mock_bucket.ls.assert_called_once_with(recursive=True)
    assert file_names == {"file1.txt", "folder/file2.txt"}

def test_list_file_names_empty(b2_manager):
    manager, mock_bucket, _ = b2_manager
    mock_bucket.ls.return_value = []

    file_names = manager.list_file_names()
    assert file_names == set()
