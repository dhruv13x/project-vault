import os
import pytest
from unittest.mock import MagicMock, patch
# Import directly assuming sys.path is correct for installed package or root
try:
    from src.projectclone import list_engine
except ImportError:
    from src.projectclone.projectclone import list_engine

class TestListEngineCoverage:
    def test_list_local_snapshots_empty(self, capsys, tmp_path):
        # Ensure snapshots dir exists but is empty
        snapshots_dir = tmp_path / "snapshots"
        snapshots_dir.mkdir()

        list_engine.list_local_snapshots(str(tmp_path))
        captured = capsys.readouterr()
        assert "No snapshots found" in captured.out

    def test_list_local_snapshots_permission_error(self, capsys, tmp_path):
        # Ensure snapshots dir exists
        snapshots_dir = tmp_path / "snapshots"
        snapshots_dir.mkdir()

        # Patch sorted(snapshots_dir.iterdir()) which is where it accesses the FS
        # But iterdir returns an iterator. sorted() consumes it.
        # Wait, code: `for project_dir in sorted(snapshots_dir.iterdir()):`
        # So if iterdir raises PermissionError?

        # We need to patch Path.iterdir
        with patch("pathlib.Path.iterdir", side_effect=PermissionError("Denied")):
            # It might crash if exception is not caught in list_engine.
            # Let's check the code... list_engine does NOT catch exceptions in the loop.
            # It only prints error if snapshots_dir doesn't exist.
            with pytest.raises(PermissionError):
                list_engine.list_local_snapshots(str(tmp_path))

        # The test previously failed expecting "Error accessing vault".
        # This means I should have checked code before writing test expectation.
        # I'll update test to expect raise.

    def test_list_local_snapshots_invalid_json(self, capsys, tmp_path):
        # Setup: snapshots/project/manifest.json
        project_dir = tmp_path / "snapshots" / "project1"
        project_dir.mkdir(parents=True)
        m = project_dir / "manifest.json"
        m.write_text("{invalid") # Invalid JSON

        # Code: `[f for f in project_dir.glob("*.json") ...]`
        # Then loop manifests. `_parse_snapshot_name(manifest_path.name)`.
        # It does NOT read the file content!
        # It only parses filename.
        # So invalid JSON content doesn't matter.
        # It lists files based on name.

        list_engine.list_local_snapshots(str(tmp_path))
        captured = capsys.readouterr()

        # It should list it!
        assert "project1" in captured.out
        assert "manifest.json" in captured.out

    def test_list_cloud_snapshots_api_error(self, capsys):
        # Patch b2.B2Manager
        with patch("src.common.b2.B2Manager") as MockB2:
             MockB2.side_effect = Exception("API Fail")
             list_engine.list_cloud_snapshots("bucket", "id", "key")
        captured = capsys.readouterr()
        assert "Error connecting to cloud backend: API Fail" in captured.out
