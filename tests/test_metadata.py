import os
import json
import pytest
from unittest.mock import patch
from datetime import datetime, timezone
import platform
import socket
from src.common import manifest

@pytest.fixture
def mock_platform_socket():
    with patch("platform.system", return_value="TestOS") as mock_os, \
         patch("socket.gethostname", return_value="test-host") as mock_host:
        yield mock_os, mock_host

def test_create_snapshot_structure_metadata(mock_platform_socket):
    """
    Test that create_snapshot_structure includes the required metadata:
    source_os, hostname, and created_at.
    """
    mock_os, mock_host = mock_platform_socket
    source_path = "/tmp/test_source"

    with patch("src.common.manifest.datetime") as mock_datetime:
        mock_now = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat = datetime.fromisoformat # Keep original method if needed

        snapshot = manifest.create_snapshot_structure(source_path)

        assert snapshot["source_os"] == "TestOS"
        assert snapshot["hostname"] == "test-host"
        assert snapshot["created_at"] == mock_now.isoformat()
        assert snapshot["timestamp"] == mock_now.isoformat() # Existing field
        assert snapshot["version"] == manifest.MANIFEST_VERSION

        # Verify calls
        mock_os.assert_called_once()
        mock_host.assert_called_once()

def test_save_manifest_metadata(tmp_path, mock_platform_socket):
    """
    Test that the saved manifest contains the metadata.
    """
    snapshot_data = {
        "version": 2,
        "timestamp": "2023-10-26T12:00:00+00:00",
        "created_at": "2023-10-26T12:00:00+00:00",
        "source_os": "TestOS",
        "hostname": "test-host",
        "source_path": str(tmp_path / "source"),
        "files": {}
    }

    snapshots_dir = tmp_path / "snapshots"

    manifest_path = manifest.save_manifest(snapshot_data, str(snapshots_dir), "test_project")

    with open(manifest_path, "r") as f:
        loaded_data = json.load(f)

    assert loaded_data["source_os"] == "TestOS"
    assert loaded_data["hostname"] == "test-host"
    assert loaded_data["created_at"] == "2023-10-26T12:00:00+00:00"
