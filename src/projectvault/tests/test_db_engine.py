import unittest
import os
import sys
import json
import gzip
from unittest.mock import MagicMock, patch, ANY
import subprocess

from src.projectvault.engines.db_engine import DatabaseEngine

class TestDatabaseEngine(unittest.TestCase):
    def setUp(self):
        self.config = {
            "driver": "postgres",
            "dbname": "test_db",
            "host": "localhost",
            "port": 5432,
            "user": "admin",
            "password": "password"
        }
        self.engine = DatabaseEngine("postgres", self.config)

    def test_init_invalid_driver(self):
        with self.assertRaises(ValueError):
            DatabaseEngine("invalid_driver", {})

    @patch("src.projectvault.engines.db_engine.subprocess.run")
    @patch("src.projectvault.engines.db_engine.subprocess.Popen")
    @patch("src.projectclone.cas_engine.backup_to_vault")
    @patch("tempfile.NamedTemporaryFile")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.unlink")
    @patch("os.replace")
    def test_backup(self, mock_replace, mock_unlink, mock_temp_dir, mock_temp_file, mock_backup_to_vault, mock_popen, mock_run):
        # Setup mocks
        mock_run.return_value.returncode = 0

        mock_process = MagicMock()
        mock_process.stdout.read.side_effect = [b"chunk1", b"chunk2", b""] # Simulate stream
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Mock temp file context
        mock_file = MagicMock()
        mock_file.name = "/tmp/dummy_dump.sql.gz"
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock temp dir context
        mock_dir = MagicMock()
        mock_dir.__enter__.return_value = "/tmp/dir"
        mock_temp_dir.return_value = mock_dir

        # Mock cas_engine return
        mock_backup_to_vault.return_value = "/vault/snapshots/manifest.json"

        # Mock manifest modification
        with patch("src.projectvault.engines.db_engine.open", unittest.mock.mock_open(read_data='{"files": {}}')) as mock_file_open:
            manifest_path = self.engine.backup("/vault", "test_project")

        self.assertEqual(manifest_path, "/vault/snapshots/manifest.json")

        # Verify subprocess called correctly
        mock_popen.assert_called_with(ANY, stdout=subprocess.PIPE, stderr=ANY, env=ANY, bufsize=-1)

        # Verify cas_engine called
        mock_backup_to_vault.assert_called_once()

    @patch("src.projectvault.engines.db_engine.subprocess.run")
    @patch("src.projectvault.engines.db_engine.subprocess.Popen")
    @patch("src.projectclone.cas_engine.backup_to_vault")
    @patch("tempfile.NamedTemporaryFile")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.unlink")
    @patch("os.replace")
    @patch("src.projectclone.sync_engine.sync_to_cloud")
    def test_backup_with_cloud(self, mock_sync, mock_replace, mock_unlink, mock_temp_dir, mock_temp_file, mock_backup_to_vault, mock_popen, mock_run):
        # Setup mocks
        mock_run.return_value.returncode = 0
        mock_process = MagicMock()
        mock_process.stdout.read.side_effect = [b"", b""]
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_temp_file.return_value.__enter__.return_value.name = "/tmp/dummy_dump.sql.gz"
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/dir"
        mock_backup_to_vault.return_value = "/vault/snapshots/manifest.json"

        credentials_module = MagicMock()
        credentials_module.resolve_credentials.return_value = ("key", "secret", "source")

        with patch("src.projectvault.engines.db_engine.open", unittest.mock.mock_open(read_data='{"files": {}}')):
            self.engine.backup("/vault", "test_project", cloud_sync=True, credentials_module=credentials_module, bucket="mybucket")

        mock_sync.assert_called_once()

    def test_resolve_password(self):
        # Case 1: Password in config
        self.engine.config["password"] = "config_pass"
        self.engine._resolve_password()
        self.assertEqual(self.engine.config["password"], "config_pass")

        # Case 2: Password via credentials module
        self.engine.config["password"] = None
        mock_creds = MagicMock()
        mock_creds.get_full_env.return_value = {"PV_DB_PASSWORD": "env_pass"}
        self.engine._resolve_password(mock_creds)
        self.assertEqual(self.engine.config["password"], "env_pass")

    @patch("src.projectvault.engines.db_engine.subprocess.run")
    @patch("src.projectrestore.restore_engine.restore_snapshot")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.walk")
    @patch("src.projectvault.engines.db_engine.open", new_callable=unittest.mock.mock_open, read_data='{"snapshot_type": "database"}')
    @patch("subprocess.Popen")
    def test_restore(self, mock_popen, mock_open, mock_walk, mock_temp_dir, mock_restore_snapshot, mock_run):
         # Setup mocks
        mock_run.return_value.returncode = 0

        mock_dir = MagicMock()
        mock_dir.__enter__.return_value = "/tmp/dir"
        mock_temp_dir.return_value = mock_dir

        # Mock finding sql file
        mock_walk.return_value = [("/tmp/dir", [], ["dump.sql"])]

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        self.engine.restore("/vault/snapshots/manifest.json", "/vault")

        # Verify verification command ran (since force=False)
        mock_run.assert_called()

        # Verify restore command ran
        mock_popen.assert_called()

    @patch("src.projectvault.engines.db_engine.subprocess.run")
    @patch("src.projectrestore.restore_engine.restore_snapshot")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.walk")
    @patch("src.projectvault.engines.db_engine.open", new_callable=unittest.mock.mock_open, read_data='{"snapshot_type": "database"}')
    @patch("subprocess.Popen")
    def test_restore_compressed(self, mock_popen, mock_open, mock_walk, mock_temp_dir, mock_restore_snapshot, mock_run):
        # Setup mocks
        mock_run.return_value.returncode = 0
        mock_dir = MagicMock()
        mock_dir.__enter__.return_value = "/tmp/dir"
        mock_temp_dir.return_value = mock_dir

        # Mock finding compressed sql file
        mock_walk.return_value = [("/tmp/dir", [], ["dump.sql.gz"])]

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_process.stdout.close.return_value = None
        mock_popen.return_value = mock_process

        self.engine.restore("/vault/snapshots/manifest.json", "/vault")

        # Verify three Popen calls (gzip -dc, sed filter, and psql)
        self.assertEqual(mock_popen.call_count, 3)

    @patch("src.projectvault.engines.db_engine.subprocess.run")
    @patch("src.projectrestore.restore_engine.restore_snapshot")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.walk")
    @patch("src.projectvault.engines.db_engine.open", new_callable=unittest.mock.mock_open, read_data='{"snapshot_type": "database"}')
    @patch("subprocess.Popen")
    def test_restore_force(self, mock_popen, mock_open, mock_walk, mock_temp_dir, mock_restore_snapshot, mock_run):
        mock_run.return_value.returncode = 0
        mock_dir = MagicMock()
        mock_dir.__enter__.return_value = "/tmp/dir"
        mock_temp_dir.return_value = mock_dir
        mock_walk.return_value = [("/tmp/dir", [], ["dump.sql"])]

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        self.engine.restore("/vault/snapshots/manifest.json", "/vault", force=True)

        # Should verify drop and create commands were run
        # We can check mock_run calls
        # 3 calls: drop, create, verify(maybe?), restore?
        # restore() with force does drop, create, then restore_cmd
        # drop, create are subprocess.run
        # restore_cmd is subprocess.Popen

        self.assertEqual(mock_run.call_count, 2) # drop and create

    @patch("src.projectvault.engines.db_engine.subprocess.run")
    def test_verify_connection_fail(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, ["psql"], stderr=b"Connection failed")

        with self.assertRaises(ConnectionError):
            self.engine.backup("/vault", "test_project")
