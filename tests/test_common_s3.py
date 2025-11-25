# tests/test_common_s3.py

import pytest
from unittest.mock import patch, MagicMock
from common.s3 import S3Manager
from botocore.exceptions import ClientError

@pytest.fixture
def mock_boto3_client():
    with patch("boto3.client") as mock:
        yield mock

def test_init(mock_boto3_client):
    key_id = "key"
    secret_key = "secret"
    bucket_name = "bucket"
    endpoint = "https://example.com"

    manager = S3Manager(key_id, secret_key, bucket_name, endpoint)

    mock_boto3_client.assert_called_once_with(
        service_name='s3',
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret_key
    )
    assert manager.client == mock_boto3_client.return_value
    assert manager.bucket_name == bucket_name

def test_upload_file(mock_boto3_client):
    manager = S3Manager("k", "s", "bucket")
    local = "local.txt"
    remote = "remote.txt"

    manager.upload_file(local, remote)

    manager.client.upload_file.assert_called_once_with(local, "bucket", remote)

def test_upload_file_error(mock_boto3_client, capsys):
    manager = S3Manager("k", "s", "bucket")
    manager.client.upload_file.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "upload_file")

    with pytest.raises(ClientError):
        manager.upload_file("local", "remote")

    captured = capsys.readouterr()
    assert "Error uploading" in captured.out

def test_download_file(mock_boto3_client):
    manager = S3Manager("k", "s", "bucket")
    local = "/tmp/local.txt"
    remote = "remote.txt"

    with patch("os.makedirs") as mock_makedirs:
        manager.download_file(remote, local)
        mock_makedirs.assert_called_once_with("/tmp", exist_ok=True)

    manager.client.download_file.assert_called_once_with("bucket", remote, local)

def test_download_file_error(mock_boto3_client, capsys):
    manager = S3Manager("k", "s", "bucket")
    manager.client.download_file.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "download_file")

    with patch("os.makedirs"):
        with pytest.raises(ClientError):
            manager.download_file("remote", "local")

    captured = capsys.readouterr()
    assert "Error downloading" in captured.out

def test_list_file_names(mock_boto3_client):
    manager = S3Manager("k", "s", "bucket")
    paginator = MagicMock()
    manager.client.get_paginator.return_value = paginator

    # Mock pagination with 2 pages
    paginator.paginate.return_value = [
        {'Contents': [{'Key': 'file1'}, {'Key': 'file2'}]},
        {'Contents': [{'Key': 'file3'}]}
    ]

    objects = manager.list_file_names()

    manager.client.get_paginator.assert_called_once_with('list_objects_v2')
    paginator.paginate.assert_called_once_with(Bucket="bucket")
    assert objects == {'file1', 'file2', 'file3'}

def test_list_file_names_empty(mock_boto3_client):
    manager = S3Manager("k", "s", "bucket")
    paginator = MagicMock()
    manager.client.get_paginator.return_value = paginator
    paginator.paginate.return_value = [{}] # Empty page

    objects = manager.list_file_names()

    assert objects == set()

def test_list_file_names_error(mock_boto3_client, capsys):
    manager = S3Manager("k", "s", "bucket")
    paginator = MagicMock()
    manager.client.get_paginator.return_value = paginator
    paginator.paginate.side_effect = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "list_objects_v2")

    with pytest.raises(ClientError):
        manager.list_file_names()

    captured = capsys.readouterr()
    assert "Error listing objects" in captured.out
