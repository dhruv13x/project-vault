import sys
import pytest
from unittest.mock import MagicMock, patch
from src.projectrestore import cli

class TestProjectRestoreCliCoverage:
    def test_main_invalid_manifest_arg(self):
        # projectrestore does not have 'restore' command. It uses 'vault-restore' or default.
        # Default is archive restore.
        # We should test the 'vault-restore' command if that's what we meant by 'restore manifest.json'
        with patch.object(sys, 'argv', ['src.projectrestore', 'vault-restore', 'manifest.json', 'dest']):
             with patch("src.projectrestore.cli.restore_engine.restore_snapshot", side_effect=FileNotFoundError("Manifest missing")):
                 with pytest.raises(SystemExit) as exc:
                     cli.main()
                 assert exc.value.code == 1

    def test_main_permission_error(self):
        with patch.object(sys, 'argv', ['src.projectrestore', 'vault-restore', 'manifest.json', 'dest']):
             with patch("src.projectrestore.cli.restore_engine.restore_snapshot", side_effect=PermissionError("Denied")):
                 with pytest.raises(SystemExit) as exc:
                     cli.main()
                 assert exc.value.code == 1

    def test_cli_version_flag(self, capsys):
        with patch.object(sys, 'argv', ['src.projectrestore', '--version']):
            with pytest.raises(SystemExit):
                cli.main()
        captured = capsys.readouterr()
        assert "src.projectrestore" in captured.out or "src.projectrestore" in captured.err
