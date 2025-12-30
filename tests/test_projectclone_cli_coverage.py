import sys
import pytest
from unittest.mock import MagicMock, patch
from src.projectclone import cli

class TestProjectCloneCliCoverage:
    def test_main_no_args_prints_help(self, capsys):
        # projectclone without args prints help and exits 0 in parse_args
        with patch.object(sys, 'argv', ['src.projectclone']):
             with pytest.raises(SystemExit) as exc:
                 cli.main()
             assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "Usage:" in captured.out or "Help:" in captured.out

    def test_main_invalid_command(self, capsys):
        # projectclone <note>
        # 'invalid_command' is interpreted as 'short_note'.
        # It then prompts for confirmation because it's about to backup.
        # We mock input to abort.
        with patch.object(sys, 'argv', ['src.projectclone', 'invalid_command']):
             with patch("builtins.input", side_effect=["n"]): # Abort by user
                 with pytest.raises(SystemExit) as exc:
                     cli.main()
                 assert exc.value.code == 1 # Aborted by user
        captured = capsys.readouterr()
        assert "Aborted by user" in captured.out

    def test_main_interrupt(self):
        # Patch ArgumentParser.parse_args to simulate Ctrl+C during parsing
        # cli.main() does NOT catch KeyboardInterrupt (it propagates).
        # So we expect KeyboardInterrupt.
        with patch("argparse.ArgumentParser.parse_args", side_effect=KeyboardInterrupt):
             with patch.object(sys, 'argv', ['src.projectclone', 'status']):
                 with pytest.raises(KeyboardInterrupt):
                     cli.main()

    def test_main_general_exception(self, capsys):
        # Patch something inside main to raise Exception
        with patch("src.projectclone.cli.ensure_dir", side_effect=Exception("Crash")):
             with patch.object(sys, 'argv', ['src.projectclone', 'note', '--yes']):
                 with pytest.raises(SystemExit) as exc:
                     cli.main()
                 assert exc.value.code == 2
        captured = capsys.readouterr()
        assert "ERROR: Could not create destination directory" in captured.out
