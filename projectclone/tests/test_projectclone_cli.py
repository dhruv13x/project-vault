import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from projectclone import cli

@pytest.fixture
def mock_sys_argv():
    with patch.object(sys, 'argv', ['create_backup.py', 'test_note']):
        yield

@pytest.fixture
def mock_sys_exit():
    with patch('sys.exit') as mock_exit:
        yield mock_exit

@pytest.fixture
def mock_cwd(tmp_path):
    with patch('pathlib.Path.cwd', return_value=tmp_path):
        yield tmp_path

@pytest.fixture
def mock_walk_stats():
    with patch('projectclone.cli.walk_stats', return_value=(10, 1000)) as mock:
        yield mock

class TestCLI:
    def test_cli_yes_flag_skips_prompt(self, mock_sys_argv, mock_cwd, mock_walk_stats, tmp_path):
        sys.argv = ['create_backup.py', 'test_note', '--yes', '--dest', str(tmp_path)]

        with patch('projectclone.cli.copy_tree_atomic') as mock_copy, \
             patch('builtins.input') as mock_input, \
             patch('projectclone.cli.print_logo'):

            cli.main()

            mock_input.assert_not_called()
            mock_copy.assert_called_once()

    def test_manifest_sha_enabled(self, mock_sys_argv, mock_cwd, mock_walk_stats, tmp_path):
        sys.argv = ['create_backup.py', 'test_note', '--yes', '--dest', str(tmp_path), '--manifest-sha']

        with patch('projectclone.cli.copy_tree_atomic') as mock_copy, \
             patch('projectclone.cli.print_logo'):

            cli.main()

            args, kwargs = mock_copy.call_args
            assert kwargs.get('manifest_sha') is True

    def test_invalid_exclude_patterns(self, mock_sys_argv, mock_cwd, mock_walk_stats, tmp_path):
        # The CLI currently just passes excludes to walk_stats/copy_tree_atomic.
        # We verify they are passed correctly.
        sys.argv = ['create_backup.py', 'test_note', '--yes', '--dest', str(tmp_path), '--exclude', '*.pyc', '--exclude', '__pycache__']

        with patch('projectclone.cli.copy_tree_atomic') as mock_copy, \
             patch('projectclone.cli.print_logo'):

            cli.main()

            args, kwargs = mock_copy.call_args
            assert kwargs.get('excludes') == ['*.pyc', '__pycache__']

    def test_keyboard_interrupt_during_execution(self, mock_sys_argv, mock_cwd, mock_walk_stats, tmp_path, mock_sys_exit):
        sys.argv = ['create_backup.py', 'test_note', '--yes', '--dest', str(tmp_path)]

        with patch('projectclone.cli.copy_tree_atomic', side_effect=KeyboardInterrupt), \
             patch('projectclone.cli.print_logo'), \
             patch('projectclone.cli.cleanup_state.cleanup') as mock_cleanup:

            # main calls cleanup on Exception, but KeyboardInterrupt might be caught by system if not handled explicitly in main
            # In cli.py:
            # try:
            # ...
            # except Exception as e:
            # ...
            # finally:
            # ...

            # KeyboardInterrupt does not inherit from Exception, so it propagates up.
            # But wait, looking at cli.py:
            # It only catches Exception.
            # So KeyboardInterrupt should crash the program (which is expected) or be caught if wrapped.

            with pytest.raises(KeyboardInterrupt):
                cli.main()

            # If it raises, cleanup in 'finally' block or exception handler?
            # The code has `except Exception`. KeyboardInterrupt is not caught there.
            # The code does NOT have a except KeyboardInterrupt block in main() (unlike src/cli.py).

    def test_logfile_contains_markers(self, mock_sys_argv, mock_cwd, mock_walk_stats, tmp_path):
        dest = tmp_path / "backups"
        dest.mkdir()
        sys.argv = ['create_backup.py', 'test_note', '--yes', '--dest', str(dest)]

        with patch('projectclone.cli.copy_tree_atomic'), \
             patch('projectclone.cli.print_logo'):

            cli.main()

            # Find log file
            log_files = list(dest.glob("*.log"))
            assert len(log_files) == 1
            content = log_files[0].read_text()
            assert "Starting backup" in content
            assert "Backup finished successfully" in content

    def test_vault_subcommand(self, mock_sys_exit):
        sys.argv = ['create_backup.py', 'vault', 'src_dir', 'vault_dir']

        with patch('projectclone.cas_engine.backup_to_vault') as mock_backup, \
             patch('projectclone.cli.print_logo'):

            cli.main()

            mock_backup.assert_called_once()
            args, _ = mock_backup.call_args
            # args are absolute paths
            assert args[0].endswith('src_dir')
            assert args[1].endswith('vault_dir')

    def test_archive_mode(self, mock_sys_argv, mock_cwd, mock_walk_stats, tmp_path):
        sys.argv = ['create_backup.py', 'test_note', '--yes', '--dest', str(tmp_path), '--archive']

        with patch('projectclone.cli.create_archive') as mock_create, \
             patch('projectclone.cli.atomic_move') as mock_move, \
             patch('projectclone.cli.print_logo'):

             # Mock make_unique_path to return the input path (simplified)
             with patch('projectclone.cli.make_unique_path', side_effect=lambda p: p):
                cli.main()

                mock_create.assert_called_once()
                mock_move.assert_called() # Archive moved to final dest

