# tests/test_integration_logging.py


import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open

from src.projectclone import diff_engine, list_engine, status_engine, backup
from src import cli

class TestFinalCoverage:

    def test_diff_engine_object_missing_real(self, tmp_path, capsys):
        vault = tmp_path / "vault"
        vault.mkdir()
        src = tmp_path / "src"
        src.mkdir()
        (src / "f").touch()

        # Project name is "src"
        snapshots_dir = vault / "snapshots" / "src"
        snapshots_dir.mkdir(parents=True)

        # Create valid snapshot
        (snapshots_dir / "s.json").write_text('{"files": {"f": "h"}, "timestamp": "now"}')

        # No object 'h'
        diff_engine.show_diff(str(src), str(vault), str(src/"f"))
        captured = capsys.readouterr()

        if "missing in vault" not in captured.out:
             print(f"DEBUG OUT: {captured.out}")

        assert "missing in vault" in captured.out

    def test_status_engine_print_loop_break(self, tmp_path, capsys):
        src = tmp_path / "src"
        vault = tmp_path / "vault"
        vault.mkdir()

        files = [f"f{i}" for i in range(15)]
        stat = {
            "project": "p",
            "snapshot_exists": True,
            "snapshot_time": "t",
            "new_files": [],
            "modified_files": files,
            "deleted_files": [],
            "total_scanned": 100
        }

        with patch("src.projectclone.status_engine.get_local_status", return_value=stat):
            status_engine.show_status(str(src), str(vault))

        captured = capsys.readouterr()
        assert "...and 5 more" in captured.out

    def test_get_cloud_status_s3_success(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()

        with patch("src.common.s3.S3Manager") as mock_s3:
            inst = mock_s3.return_value
            inst.list_file_names.return_value = []

            status = status_engine.get_cloud_status(str(vault), "bucket", "endpoint", "id", "key")
            assert status["connected"] is True
            assert status["error"] is None
            # Covers S3 branch

    def test_list_local_snapshots_file_handling(self, tmp_path, capsys):
        vault = tmp_path / "vault"
        vault.mkdir()
        snapshots = vault / "snapshots"
        snapshots.mkdir()
        # Create a file in snapshots dir to trigger 'if project_dir.is_dir()' check false branch?
        # list_engine loop: for project_dir in sorted(snapshots_dir.iterdir()):
        (snapshots / "file").touch()
        (snapshots / "dir").mkdir()

        list_engine.list_local_snapshots(str(vault))
        captured = capsys.readouterr()
        # Should ignore 'file' and process 'dir' (empty)
        assert "No snapshots found" in captured.out

    def test_backup_log_branches(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "f1").touch()
        dest = tmp_path / "dest"
        dest.mkdir()

        log_fp = MagicMock()
        # Allow write to succeed first then fail?
        # We want to cover 'except Exception: pass' in log writing blocks.
        # This happens if log_fp.write raises.

        log_fp.write.side_effect = Exception("Log fail")

        # backup.copy_tree_atomic should survive this
        backup.copy_tree_atomic(src, dest, "backup", log_fp=log_fp)

    def test_create_archive_log_branches(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "f1").touch()
        dest = tmp_path / "dest"
        dest.mkdir()

        log_fp = MagicMock()
        log_fp.write.side_effect = Exception("Log fail")

        # backup.create_archive should survive log failure
        backup.create_archive(src, dest / "a.tar.gz", log_fp=log_fp)

    def test_rsync_log_branches(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()

        log_fp = MagicMock()
        log_fp.write.side_effect = Exception("Log fail")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            backup.rsync_incremental(src, dest, "backup", None, log_fp=log_fp)

    def test_cli_check_integrity_command(self, tmp_path):
        with patch.object(sys, 'argv', ['pv', 'check-integrity', str(tmp_path)]):
            with patch("src.projectclone.integrity_engine.verify_vault") as mock_verify:
                 cli.main()
                 mock_verify.assert_called()

    def test_cli_gc_command(self, tmp_path):
        with patch.object(sys, 'argv', ['pv', 'gc', str(tmp_path)]):
             with patch("src.projectclone.gc_engine.run_garbage_collection") as mock_gc:
                 cli.main()
                 mock_gc.assert_called()
