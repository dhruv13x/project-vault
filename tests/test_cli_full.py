# tests/test_cli_full.py


import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from src import cli

class TestCliFull:

    @patch("src.cli.credentials.get_full_env", return_value={})
    def test_cli_commands_dispatch(self, mock_get_env):
        # Verify dispatching for all commands
        commands = [
            ("gc", "src.projectclone.gc_engine.run_garbage_collection"),
            ("check-integrity", "src.projectclone.integrity_engine.verify_vault"),
            ("push", "src.projectclone.sync_engine.sync_to_cloud"),
            ("pull", "src.projectclone.sync_engine.sync_from_cloud"),
            ("list", "src.projectclone.list_engine.list_local_snapshots"),
            ("diff", "src.projectclone.diff_engine.show_diff"),
            ("checkout", "src.projectclone.checkout_engine.checkout_file"),
            ("status", "src.projectclone.status_engine.show_status"),
        ]

        for cmd, target in commands:
            if cmd in ["push", "pull"]:
                with patch("src.cli.credentials.resolve_credentials", return_value=("id", "key", "MockSource")):
                    with patch(target) as mock_target:
                        with patch.object(sys, 'argv', ['pv', cmd, '/tmp/vault', '--bucket', 'b']):
                            cli.main()
                        mock_target.assert_called()
            elif cmd == "list":
                with patch(target) as mock_target:
                    with patch.object(sys, 'argv', ['pv', cmd, '/tmp/vault']):
                        cli.main()
                    mock_target.assert_called()
            elif cmd == "gc":
                with patch(target) as mock_target:
                    with patch.object(sys, 'argv', ['pv', cmd, '/tmp/vault']):
                        cli.main()
                    mock_target.assert_called()
            elif cmd == "check-integrity":
                with patch(target) as mock_target:
                    with patch.object(sys, 'argv', ['pv', cmd, '/tmp/vault']):
                        cli.main()
                    mock_target.assert_called()
            elif cmd == "diff":
                with patch(target) as mock_target:
                    with patch.object(sys, 'argv', ['pv', cmd, 'file', '/tmp/vault']):
                        cli.main()
                    mock_target.assert_called()
            elif cmd == "checkout":
                with patch(target) as mock_target:
                    with patch.object(sys, 'argv', ['pv', cmd, 'file', '/tmp/vault']):
                        cli.main()
                    mock_target.assert_called()
            elif cmd == "status":
                with patch(target) as mock_target:
                    with patch.object(sys, 'argv', ['pv', cmd, 'src', '/tmp/vault']):
                        cli.main()
                    mock_target.assert_called()

    def test_cli_push_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault', 'bucket': 'bkt'}):
            with patch("src.cli.credentials.resolve_credentials", return_value=("id", "key", "MockSource")):
                with patch("src.projectclone.sync_engine.sync_to_cloud", side_effect=Exception("Push fail")):
                    with patch.object(sys, 'argv', ['pv', 'push']):
                        with pytest.raises(SystemExit):
                            cli.main()

    def test_cli_pull_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault', 'bucket': 'bkt'}):
            with patch("src.cli.credentials.resolve_credentials", return_value=("id", "key", "MockSource")):
                with patch("src.projectclone.sync_engine.sync_from_cloud", side_effect=Exception("Pull fail")):
                    with patch.object(sys, 'argv', ['pv', 'pull']):
                        with pytest.raises(SystemExit):
                            cli.main()

    def test_cli_list_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("src.projectclone.list_engine.list_local_snapshots", side_effect=Exception("List fail")):
                with patch.object(sys, 'argv', ['pv', 'list']):
                    with pytest.raises(SystemExit):
                        cli.main()

    def test_cli_checkout_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("src.projectclone.checkout_engine.checkout_file", side_effect=Exception("Checkout fail")):
                with patch.object(sys, 'argv', ['pv', 'checkout', 'file']):
                    with pytest.raises(SystemExit):
                        cli.main()

    def test_cli_diff_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("src.projectclone.diff_engine.show_diff", side_effect=Exception("Diff fail")):
                with patch.object(sys, 'argv', ['pv', 'diff', 'file']):
                    with pytest.raises(SystemExit):
                        cli.main()

    def test_cli_gc_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("src.projectclone.gc_engine.run_garbage_collection", side_effect=Exception("GC fail")):
                with patch.object(sys, 'argv', ['pv', 'gc']):
                    with pytest.raises(SystemExit):
                        cli.main()

    def test_cli_integrity_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("src.projectclone.integrity_engine.verify_vault", side_effect=Exception("Integrity fail")):
                with patch.object(sys, 'argv', ['pv', 'check-integrity']):
                    with pytest.raises(SystemExit):
                        cli.main()

    def test_cli_vault_cmd_exception(self):
        with patch("src.common.config.load_project_config", return_value={'vault_path': '/tmp/vault'}):
            with patch("src.projectclone.cas_engine.backup_to_vault", side_effect=Exception("Vault fail")):
                with patch.object(sys, 'argv', ['pv', 'vault', 'src', 'dst']):
                    with pytest.raises(SystemExit):
                        cli.main()

    def test_cli_vault_restore_cmd_exception(self):
        with patch("src.projectrestore.restore_engine.restore_snapshot", side_effect=Exception("Restore fail")):
            with patch.object(sys, 'argv', ['pv', 'vault-restore', 'man', 'dest']):
                with pytest.raises(SystemExit):
                    cli.main()
