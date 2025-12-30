import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import json
import subprocess
import gzip
import tempfile

from src.projectvault.engines.db_engine import DatabaseEngine
from src.projectvault.drivers.postgres import PostgresDriver

class TestPostgresDriver(unittest.TestCase):
    def setUp(self):
        self.driver = PostgresDriver()
        self.config = {
            "driver": "postgres",
            "host": "localhost",
            "port": 5432,
            "user": "admin",
            "dbname": "testdb",
            "password": "secret"
        }

    def test_get_backup_command(self):
        cmd = self.driver.get_backup_command(self.config)
        expected = ["pg_dump", "-h", "localhost", "-p", "5432", "-U", "admin", "--clean", "--if-exists", "--no-owner", "--no-acl", "testdb"]
        self.assertEqual(cmd, expected)

    def test_get_restore_command(self):
        cmd = self.driver.get_restore_command(self.config)
        expected = ["psql", "-h", "localhost", "-p", "5432", "-U", "admin", "-d", "testdb", "-v", "ON_ERROR_STOP=1"]
        self.assertEqual(cmd, expected)

    def test_get_verification_command(self):
        cmd = self.driver.get_verification_command(self.config)
        expected = ["psql", "-h", "localhost", "-p", "5432", "-U", "admin", "-d", "testdb", "-c", "SELECT 1"]
        self.assertEqual(cmd, expected)

    def test_env_password(self):
        env = self.driver._get_env(self.config)
        self.assertEqual(env.get("PGPASSWORD"), "secret")

class TestDatabaseEngine(unittest.TestCase):
    def setUp(self):
        self.config = {
            "driver": "postgres",
            "dbname": "testdb"
        }
        self.engine = DatabaseEngine("postgres", self.config)

    @patch("subprocess.Popen")
    @patch("tempfile.NamedTemporaryFile")
    @patch("tempfile.TemporaryFile")
    @patch("tempfile.TemporaryDirectory")
    @patch("src.projectclone.cas_engine.backup_to_vault")
    @patch("os.replace")
    @patch("os.unlink")
    def test_backup_success_streaming(self, mock_unlink, mock_replace, mock_cas_backup, mock_temp_dir, mock_temp_file_stderr, mock_temp_file, mock_popen):
        # Mock temp file context manager
        mock_file = MagicMock()
        mock_file.name = "/tmp/fake_dump.sql.gz"
        mock_temp_file.return_value.__enter__.return_value = mock_file

        # Mock stderr temp file
        mock_stderr = MagicMock()
        mock_temp_file_stderr.return_value.__enter__.return_value = mock_stderr

        # Mock temp dir context manager
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/fake_dir"

        # Mock subprocess Popen (pg_dump)
        # We need to simulate verify call AND pg_dump call
        # The verify call uses run(), which calls Popen underneath usually, but we mocked run() separately in previous tests.
        # Here we only mock Popen.
        # But wait, we verify first.

        # Let's mock subprocess.run as well for verification
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            process_mock = MagicMock()
            process_mock.stdout.read.side_effect = [b"chunk1", b"chunk2", b""] # Simulate stream
            process_mock.wait.return_value = 0
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Mock CAS backup return
            mock_cas_backup.return_value = "/vault/manifests/man_123.json"

            # Mock manifest tagging (open/read/write)
            with patch("src.projectvault.engines.db_engine.open", mock_open(read_data='{"id": "123"}')) as mock_file_open:
                manifest = self.engine.backup("/vault", "test_project")

            # Check that manifest path is returned (might be transformed by the code)
            self.assertTrue(manifest.endswith("man_123.json"))

            # Verify pg_dump was called with stderr redirection
            mock_popen.assert_called()
            args = mock_popen.call_args[0][0]
            kwargs = mock_popen.call_args[1]
            self.assertIn("pg_dump", args)
            self.assertEqual(kwargs['stderr'], mock_stderr)

    def test_resolve_password(self):
        mock_creds = MagicMock()
        mock_creds.get_full_env.return_value = {"PV_DB_PASSWORD": "supersecret"}

        self.engine._resolve_password(mock_creds)
        self.assertEqual(self.engine.config["password"], "supersecret")
        self.assertEqual(self.engine.env["PGPASSWORD"], "supersecret")

    @patch("src.projectrestore.restore_engine.restore_snapshot")
    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("tempfile.TemporaryDirectory")
    @patch("os.walk")
    def test_restore_success_compressed(self, mock_walk, mock_temp_dir, mock_run, mock_popen, mock_restore):
        # Mock temp dir
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/restore_dir"

        # Mock os.walk to find SQL file (compressed)
        mock_walk.return_value = [("/tmp/restore_dir", [], ["dump.sql.gz"])]

        # Mock verification
        mock_run.return_value = MagicMock(returncode=0)

        # Mock Popen calls (one for gzip -dc, one for psql)
        process_mock = MagicMock()
        process_mock.communicate.return_value = (b"", b"")
        process_mock.returncode = 0
        process_mock.stdout.close.return_value = None
        mock_popen.return_value = process_mock

        # Mock manifest read
        with patch("src.projectvault.engines.db_engine.open", mock_open(read_data='{"snapshot_type": "database"}')):
             self.engine.restore("/vault/manifest.json", "/vault")

        mock_restore.assert_called_with("/vault/manifest.json", "/tmp/restore_dir")

        # Verify three Popen calls (gzip -dc, sed filter, psql)
        self.assertEqual(mock_popen.call_count, 3)
        
        # First call should be gzip -dc
        args1 = mock_popen.call_args_list[0][0][0]
        self.assertIn("gzip", args1)
        
        # Second call should be sed
        args2 = mock_popen.call_args_list[1][0][0]
        self.assertIn("sed", args2)
        
        # Third call should be psql
        args3 = mock_popen.call_args_list[2][0][0]
        self.assertIn("psql", args3)

if __name__ == '__main__':
    unittest.main()
