import sys
import pytest
from unittest.mock import MagicMock, patch
from src import cli

class TestSrcCliCoverageV3:
    def test_check_env_command(self, capsys):
        with patch.object(sys, 'argv', ['pv', 'check-env']):
             with patch("src.cli.check_cloud_env") as mock_check:
                 cli.main()
        mock_check.assert_called()

    def test_browse_command_missing_dependency(self, capsys):
        # Simulate ImportError for textual
        # We can patch sys.modules, but cli.py imports it inside the function.
        # `from src.tui import ProjectVaultApp`
        # We can patch `builtins.__import__` but that's risky.
        # Better: patch `src.tui.ProjectVaultApp` to raise ImportError? No, import raises it.
        # Patch `src.cli.ProjectVaultApp`? It's imported inside `browse` command block.

        with patch.dict(sys.modules, {"src.tui": None}):
             # This ensures `import src.tui` raises ImportError or ModuleNotFoundError
             # But `cli.py` uses `from src.tui import ...`.
             # If sys.modules["src.tui"] is None, import might fail.
             # Let's try running it.
             with patch.object(sys, 'argv', ['pv', 'browse', 'vault']):
                 with pytest.raises(SystemExit) as exc:
                     cli.main()
                 assert exc.value.code == 1
        captured = capsys.readouterr()
        # The error message "Error: 'textual' library not found" is printed.
        # BUT if sys.modules has None, it might raise ModuleNotFoundError.
        # cli.py catches ImportError. ModuleNotFoundError inherits from ImportError.
        # So it should work if I can trigger it.

    def test_main_pass_through_backup(self):
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            with patch.object(sys, 'argv', ['pv', 'backup', 'arg']):
                cli._real_main()
            mock_module.main.assert_called()

    def test_main_pass_through_restore(self):
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            with patch.object(sys, 'argv', ['pv', 'archive-restore', 'arg']):
                cli._real_main()
            mock_module.main.assert_called()

    def test_main_pass_through_import_error(self, capsys):
        with patch("importlib.import_module", side_effect=ImportError("No module")):
            with patch.object(sys, 'argv', ['pv', 'backup', 'arg']):
                with pytest.raises(SystemExit) as exc:
                    cli._real_main()
                assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Error executing command 'backup': No module" in captured.out
