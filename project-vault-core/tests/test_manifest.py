import pytest
import os
import json
from datetime import datetime

from pv_core import manifest

@pytest.fixture
def snapshots_dir(tmp_path):
    d = tmp_path / "snapshots"
    d.mkdir()
    return d

class TestCreateSnapshotStructure:
    def test_creates_correct_structure(self):
        source = "/path/to/my/project"
        structure = manifest.create_snapshot_structure(source)
        
        assert "timestamp" in structure
        assert "source_path" in structure
        assert "files" in structure
        assert structure["files"] == {}
        
        # Check if timestamp is valid ISO format
        assert datetime.fromisoformat(structure["timestamp"])
        
        # Check if source_path is absolute
        assert os.path.isabs(structure["source_path"])
        assert structure["source_path"] == os.path.abspath(source)

class TestSaveManifest:
    def test_saves_manifest_correctly(self, snapshots_dir):
        snapshot_data = {
            "timestamp": "2023-10-27T10:00:00.123456+00:00",
            "source_path": "/test/project",
            "files": {"file.txt": "hash123"}
        }
        project_name = "my-test-project"
        
        saved_path = manifest.save_manifest(snapshot_data, str(snapshots_dir), project_name)
        
        project_dir = snapshots_dir / project_name
        assert project_dir.exists()
        
        safe_timestamp = snapshot_data["timestamp"].replace(":", "-")
        expected_filename = f"snapshot_{safe_timestamp}.json"
        expected_path = project_dir / expected_filename
        
        assert os.path.abspath(saved_path) == str(expected_path)
        assert expected_path.exists()
        
        with open(expected_path, "r") as f:
            saved_data = json.load(f)
        
        assert saved_data == snapshot_data

    def test_default_project_name(self, snapshots_dir):
        snapshot_data = {
            "timestamp": "2023-11-01T12:00:00+00:00",
            "source_path": "/another/project",
            "files": {}
        }
        
        manifest.save_manifest(snapshot_data, str(snapshots_dir))
        
        project_dir = snapshots_dir / "default"
        assert project_dir.exists()
        
        safe_timestamp = snapshot_data["timestamp"].replace(":", "-")
        expected_filename = f"snapshot_{safe_timestamp}.json"
        assert (project_dir / expected_filename).exists()

class TestLoadManifest:
    def test_loads_manifest_correctly(self, snapshots_dir):
        manifest_content = {"key": "value"}
        manifest_path = snapshots_dir / "test_manifest.json"
        manifest_path.write_text(json.dumps(manifest_content))
        
        loaded_data = manifest.load_manifest(str(manifest_path))
        
        assert loaded_data == manifest_content

    def test_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            manifest.load_manifest("non_existent_manifest.json")
            
    def test_raises_json_decode_error_for_malformed_file(self, snapshots_dir):
        manifest_path = snapshots_dir / "malformed.json"
        manifest_path.write_text("this is not json")
        
        with pytest.raises(json.JSONDecodeError):
            manifest.load_manifest(str(manifest_path))
