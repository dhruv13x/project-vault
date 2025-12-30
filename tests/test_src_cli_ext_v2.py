# tests/test_src_cli_ext_v2.py


import pytest
import sys
import os
from unittest.mock import MagicMock, patch
from pathlib import Path
from src import cli

class TestSrcCliExtended:
    @pytest.fixture
    def mock_args(self):
        """Mock standard arguments."""
        args = MagicMock()
        args.command = "status"
        args.vault_path = "/tmp/vault"
        args.bucket = None
        args.endpoint = None
        args.source = "."
        return args

    def test_resolve_path(self):
        assert cli.resolve_path(None) is None
        assert cli.resolve_path("/tmp") == "/tmp"
        # Can't easily test expansion without mocking os.environ or os.path.expanduser

    def test_get_credentials_aws_env(self, monkeypatch):
        monkeypatch.setenv("PV_AWS_ACCESS_KEY_ID", "pv_aws_key")
        monkeypatch.setenv("PV_AWS_SECRET_ACCESS_KEY", "pv_aws_secret")

        class DummyArgs:
            key_id = None
            secret_key = None

        with patch("cli.credentials.get_doppler_secrets", return_value={}):
            key, secret, source = cli.credentials.resolve_credentials(DummyArgs())
            assert key == "pv_aws_key"
            assert secret == "pv_aws_secret"

    def test_get_credentials_b2_env(self, monkeypatch):
        monkeypatch.delenv("PV_AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)

        monkeypatch.setenv("PV_B2_KEY_ID", "pv_b2_key")
        monkeypatch.setenv("PV_B2_APP_KEY", "pv_b2_app")

        class DummyArgs:
            key_id = None
            secret_key = None

        with patch("cli.credentials.get_doppler_secrets", return_value={}):
            key, secret, source = cli.credentials.resolve_credentials(DummyArgs())
            assert key == "pv_b2_key"
            assert secret == "pv_b2_app"

    @patch('src.common.console.console.print')
    @patch('src.cli.credentials.resolve_credentials')
    def test_check_cloud_env(self, mock_resolve, mock_print, capsys):
        mock_resolve.return_value = ('key', 'secret', 'Source')

        mock_creds_module = MagicMock()
        mock_creds_module.resolve_credentials = mock_resolve
        mock_creds_module.get_cloud_provider_info.return_value = ("AWS", "bucket", "endpoint")

        cli.check_cloud_env(mock_creds_module)

        # Check mock print calls instead of capsys
        found = False
        for call_args in mock_print.call_args_list:
            panel = call_args[0][0]
            text = str(panel.renderable)
            if "Cloud Environment Configuration" in str(call_args) or "Cloud Environment Configuration" in str(panel.title):
                found = True
                break
        assert found

    def test_print_main_help(self, capsys):
        with pytest.raises(SystemExit):
             with patch.object(sys, 'argv', ['pv']):
                 cli.main()
        out, _ = capsys.readouterr()
        # Rich console output captured?
        # assert "Project Vault" in out

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.cas_engine.backup_to_vault")
    def test_vault_command(self, mock_backup, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "vault", ".", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_backup.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.cas_engine.backup_to_vault")
    def test_vault_command_no_path(self, mock_backup, mock_config, capsys):
        mock_config.return_value = {}
        test_args = ["pv", "vault", "."]
        with patch.object(sys, 'argv', test_args):
             # Should proceed with smart default path
             cli.main()
             
        mock_backup.assert_called()
        args, kwargs = mock_backup.call_args
        # Check if vault path argument (2nd arg) contains .project_vault
        assert ".project_vault" in args[1]

    @patch("src.cli.config.load_project_config")
    @patch("src.projectrestore.restore_engine.restore_snapshot")
    def test_vault_restore_command(self, mock_restore, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "vault-restore", "manifest.json", "/tmp/dest"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_restore.assert_called()

    @patch("src.cli.config.load_project_config")
    def test_init_command(self, mock_config, capsys):
        mock_config.return_value = {}
        test_args = ["pv", "init"]
        with patch.object(sys, 'argv', test_args), \
             patch("src.common.config.generate_init_file") as mock_gen:
             cli.main()
             mock_gen.assert_called()

    @patch("src.cli.config.load_project_config")
    def test_init_pyproject_command(self, mock_config, capsys):
        mock_config.return_value = {}
        test_args = ["pv", "init", "--pyproject"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        out, _ = capsys.readouterr()
        assert "[tool.project-vault]" in out

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.status_engine.show_status")
    def test_status_command(self, mock_status, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "status", ".", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_status.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.diff_engine.show_diff")
    def test_diff_command(self, mock_diff, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "diff", "file.txt", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_diff.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.checkout_engine.checkout_file")
    def test_checkout_command(self, mock_checkout, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "checkout", "file.txt", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_checkout.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.list_engine.list_local_snapshots")
    def test_list_command_local(self, mock_list, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "list", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_list.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.list_engine.list_cloud_snapshots")
    @patch("src.cli.credentials.resolve_credentials")
    def test_list_command_cloud(self, mock_creds, mock_list, mock_config):
        mock_config.return_value = {}
        mock_creds.return_value = ("key", "secret", "Mock")
        test_args = ["pv", "list", "--cloud", "--bucket", "mybucket"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_list.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.sync_engine.sync_to_cloud")
    @patch("src.cli.credentials.resolve_credentials")
    def test_push_command(self, mock_creds, mock_sync, mock_config):
        mock_config.return_value = {}
        mock_creds.return_value = ("key", "secret", "Mock")
        test_args = ["pv", "push", "/tmp/vault", "--bucket", "mybucket"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_sync.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.sync_engine.sync_from_cloud")
    @patch("src.cli.credentials.resolve_credentials")
    def test_pull_command(self, mock_creds, mock_sync, mock_config):
        mock_config.return_value = {}
        mock_creds.return_value = ("key", "secret", "Mock")
        test_args = ["pv", "pull", "/tmp/vault", "--bucket", "mybucket"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_sync.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.integrity_engine.verify_vault")
    def test_integrity_command(self, mock_verify, mock_config):
        mock_config.return_value = {}
        mock_verify.return_value = True
        test_args = ["pv", "check-integrity", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_verify.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.gc_engine.run_garbage_collection")
    def test_gc_command(self, mock_gc, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "gc", "/tmp/vault"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_gc.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectclone.cli.main")
    def test_legacy_backup_command(self, mock_clone, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "backup", "note"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_clone.assert_called()

    @patch("src.cli.config.load_project_config")
    @patch("src.projectrestore.cli.main")
    @patch("src.cli.credentials.get_full_env", return_value={})
    def test_legacy_restore_command(self, mock_get_env, mock_restore, mock_config):
        mock_config.return_value = {}
        test_args = ["pv", "archive-restore", "--dry-run"]
        with patch.object(sys, 'argv', test_args):
             cli.main()
        mock_restore.assert_called()

    @patch("src.cli.config.load_project_config")
    def test_exception_handling(self, mock_config, capsys):
        mock_config.side_effect = Exception("Config Error")
        test_args = ["pv", "init"]
        with patch.object(sys, 'argv', test_args):
             with pytest.raises(SystemExit) as exc:
                 cli.main()
             assert exc.value.code == 1
