import pytest
from unittest.mock import patch, MagicMock
from src.common import s3
from botocore.exceptions import ClientError

@pytest.fixture
def mock_boto3_client():
    with patch("boto3.client") as mock:
        yield mock

def test_get_client(mock_boto3_client):
    endpoint = "https://example.com"
    key = "key"
    secret = "secret"

    client = s3.get_client(endpoint, key, secret)

    mock_boto3_client.assert_called_once_with(
        service_name='s3',
        endpoint_url=endpoint,
        aws_access_key_id=key,
        aws_secret_access_key=secret
    )
    assert client == mock_boto3_client.return_value

def test_upload_file(mock_boto3_client):
    client = MagicMock()
    bucket = "bucket"
    local = "local.txt"
    remote = "remote.txt"

    s3.upload_file(client, bucket, local, remote)

    client.upload_file.assert_called_once_with(local, bucket, remote)

def test_upload_file_error(mock_boto3_client, capsys):
    client = MagicMock()
    client.upload_file.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "upload_file")

    with pytest.raises(ClientError):
        s3.upload_file(client, "bucket", "local", "remote")

    captured = capsys.readouterr()
    assert "Error uploading" in captured.out

def test_list_existing_objects(mock_boto3_client):
    client = MagicMock()
    paginator = MagicMock()
    client.get_paginator.return_value = paginator

    # Mock pagination with 2 pages
    paginator.paginate.return_value = [
        {'Contents': [{'Key': 'file1'}, {'Key': 'file2'}]},
        {'Contents': [{'Key': 'file3'}]}
    ]

    objects = s3.list_existing_objects(client, "bucket", "prefix")

    client.get_paginator.assert_called_once_with('list_objects_v2')
    paginator.paginate.assert_called_once_with(Bucket="bucket", Prefix="prefix")
    assert objects == {'file1', 'file2', 'file3'}

def test_list_existing_objects_empty(mock_boto3_client):
    client = MagicMock()
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.return_value = [{}] # Empty page

    objects = s3.list_existing_objects(client, "bucket", "prefix")

    assert objects == set()

def test_list_existing_objects_error(mock_boto3_client, capsys):
    client = MagicMock()
    paginator = MagicMock()
    client.get_paginator.return_value = paginator
    paginator.paginate.side_effect = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "list_objects_v2")

    with pytest.raises(ClientError):
        s3.list_existing_objects(client, "bucket", "prefix")

    captured = capsys.readouterr()
    assert "Error listing objects" in captured.out
