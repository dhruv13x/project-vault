# projectclone/tests/test_list_engine_coverage.py

import pytest
import os
from unittest.mock import patch, MagicMock
from projectclone.list_engine import _parse_snapshot_name, list_cloud_snapshots

class TestListEngineCoverage:
    def test_parse_snapshot_name_valid(self):
        filename = "snapshot_2025-11-22T15-12-01.570822+00-00.json"
        assert _parse_snapshot_name(filename) == "2025-11-22 15:12:01"

    def test_parse_snapshot_name_invalid_format(self):
        filename = "invalid_format.json"
        assert _parse_snapshot_name(filename) == filename

    def test_parse_snapshot_name_value_error(self):
        # Valid structure but invalid date
        filename = "snapshot_2025-13-22T15-12-01.000000+00-00.json"
        assert _parse_snapshot_name(filename) == filename

    @patch("src.common.b2.B2Manager")
    def test_list_cloud_snapshots_b2_manager(self, mock_b2_manager):
        # Mock os.environ.get to behave like dict.get but control specific keys
        original_get = os.environ.get
        def side_effect(key, default=None):
            if key == "AWS_ACCESS_KEY_ID": return None
            return original_get(key, default)
            
        with patch("os.environ.get", side_effect=side_effect):
            list_cloud_snapshots("bucket", "key", "app")
            mock_b2_manager.assert_called_once()

    @patch("src.common.s3.S3Manager")
    def test_list_cloud_snapshots_s3_manager_via_endpoint(self, mock_s3_manager):
        # Test selection of S3Manager when endpoint provided
        list_cloud_snapshots("bucket", "key", "app", endpoint="http://endpoint")
        mock_s3_manager.assert_called_once()

    @patch("src.common.s3.S3Manager")
    def test_list_cloud_snapshots_s3_manager_via_env(self, mock_s3_manager):
        # Test selection of S3Manager when AWS env var present
        original_get = os.environ.get
        def side_effect(key, default=None):
            if key == "AWS_ACCESS_KEY_ID": return "val"
            return original_get(key, default)

        with patch("os.environ.get", side_effect=side_effect):
            list_cloud_snapshots("bucket", "key", "app")
            mock_s3_manager.assert_called_once()