# projectclone/tests/test_cloud_status.py

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from src.projectclone import status_engine

class TestCloudStatus:

    def test_get_cloud_status_logic(self, tmp_path):
        """Verify the difference calculation logic in get_cloud_status."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Setup local snapshots
        snapshots_dir = vault_path / "snapshots" / "my_project"
        snapshots_dir.mkdir(parents=True)

        # Local snapshots: 1, 2, 3
        (snapshots_dir / "snap1.json").write_text("{}")
        (snapshots_dir / "snap2.json").write_text("{}")
        (snapshots_dir / "snap3.json").write_text("{}")

        # Cloud snapshots: 1, 2, 4
        cloud_files = [
            "snapshots/my_project/snap1.json",
            "snapshots/my_project/snap2.json",
            "snapshots/my_project/snap4.json",
            "other_file.txt"
        ]

        with patch("src.common.b2.B2Manager") as mock_b2_cls:
            mock_b2 = mock_b2_cls.return_value
            mock_b2.list_file_names.return_value = cloud_files

            status = status_engine.get_cloud_status(
                str(vault_path), "bucket", None, "id", "key"
            )

            assert status["connected"] is True
            assert status["local_count"] == 3
            assert status["cloud_count"] == 3 # Only json files in snapshots/

            # Local only: snap3
            assert len(status["local_only"]) == 1
            assert "snapshots/my_project/snap3.json" in status["local_only"]

            # Cloud only: snap4
            assert len(status["cloud_only"]) == 1
            assert "snapshots/my_project/snap4.json" in status["cloud_only"]

            assert status["to_push"] == 1
            assert status["to_pull"] == 1
            assert status["synced"] is False

    def test_get_cloud_status_fully_synced(self, tmp_path):
        """Verify status when fully synced."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        snapshots_dir = vault_path / "snapshots" / "my_project"
        snapshots_dir.mkdir(parents=True)
        (snapshots_dir / "snap1.json").write_text("{}")

        with patch("src.common.b2.B2Manager") as mock_b2_cls:
            mock_b2 = mock_b2_cls.return_value
            mock_b2.list_file_names.return_value = ["snapshots/my_project/snap1.json"]

            status = status_engine.get_cloud_status(
                str(vault_path), "bucket", None, "id", "key"
            )

            assert status["synced"] is True
            assert status["to_push"] == 0
            assert status["to_pull"] == 0

    def test_show_status_integration_warning(self, tmp_path, capsys):
        """Verify the warning when the latest snapshot is not in the cloud."""
        src_path = tmp_path / "my_project"
        src_path.mkdir()

        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Local has snap2 (latest)
        snapshots_dir = vault_path / "snapshots" / "my_project"
        snapshots_dir.mkdir(parents=True)
        (snapshots_dir / "snap1.json").write_text('{"timestamp": "2023-01-01"}')
        (snapshots_dir / "snap2.json").write_text('{"timestamp": "2023-01-02"}') # Latest

        # Cloud only has snap1
        cloud_files = ["snapshots/my_project/snap1.json"]

        # Mock get_local_status to return consistent data
        mock_local_status = {
            "project": "my_project",
            "snapshot_exists": True,
            "snapshot_time": "2023-01-02",
            "new_files": [], "modified_files": [], "deleted_files": [],
            "total_scanned": 0
        }

        with patch("src.projectclone.status_engine.get_local_status", return_value=mock_local_status):
            with patch("src.common.b2.B2Manager") as mock_b2_cls:
                mock_b2 = mock_b2_cls.return_value
                mock_b2.list_file_names.return_value = cloud_files

                cloud_config = {"bucket": "b", "key_id": "k", "app_key": "s"}

                status_engine.show_status(
                    str(src_path), str(vault_path), cloud_config
                )

        captured = capsys.readouterr()

        # Check for substrings because of potential rich formatting
        assert "Local is ahead by 1 snapshots" in captured.out
        # Adjust for possible formatting or lack of full path in output
        # Based on actual output: "Warning: The latest snapshot (snap2.json) is NOT in the cloud!"
        assert "Warning: The latest snapshot" in captured.out
        assert "snap2.json) is NOT in the cloud" in captured.out
        assert "Run pv push" in captured.out

    def test_show_status_cloud_error_handling(self, tmp_path, capsys):
        """Verify error handling during cloud check."""
        src_path = tmp_path / "src"
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Mocking get_local_status to return total_scanned to avoid KeyError
        with patch("src.projectclone.status_engine.get_local_status", return_value={"snapshot_exists": False, "total_scanned": 10}):
            with patch("src.common.b2.B2Manager", side_effect=Exception("Network Error 500")):

                cloud_config = {"bucket": "b", "key_id": "k", "app_key": "s"}
                status_engine.show_status(str(src_path), str(vault_path), cloud_config)

        captured = capsys.readouterr()
        assert "Error connecting to cloud" in captured.out
        assert "Network Error 500" in captured.out
