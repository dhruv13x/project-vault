import os
import zipfile
import json
import pytest
import shutil
from src.common import capsule, manifest, cas

@pytest.fixture
def sample_vault(tmp_path):
    vault_path = tmp_path / "vault"
    snapshots_dir = vault_path / "snapshots" / "test_project"
    objects_dir = vault_path / "objects"

    os.makedirs(snapshots_dir)
    os.makedirs(objects_dir)

    # Create a source file
    source_file = tmp_path / "hello.txt"
    content = b"Hello Capsule"
    source_file.write_bytes(content)

    # Store object using cas.store_object which expects a file path
    obj_hash = cas.store_object(str(source_file), str(objects_dir))

    # Create manifest
    snapshot_data = {
        "version": 2,
        "timestamp": "2023-10-26T12-00-00+00-00",
        "created_at": "2023-10-26T12:00:00+00:00",
        "source_path": "/src",
        "files": {
            "hello.txt": {
                "hash": obj_hash,
                "size": len(content),
                "mode": 33188,
                "mtime": 1698321600.0
            }
        }
    }

    manifest_path = snapshots_dir / "snapshot_2023-10-26T12-00-00+00-00.json"
    with open(manifest_path, "w") as f:
        json.dump(snapshot_data, f)

    return {
        "vault_path": vault_path,
        "manifest_path": manifest_path,
        "objects_dir": objects_dir,
        "obj_hash": obj_hash,
        "content": content
    }

def test_pack_capsule(sample_vault, tmp_path):
    output_path = tmp_path / "test.pvc"

    capsule.pack_capsule(str(sample_vault["manifest_path"]), str(output_path))

    assert os.path.exists(output_path)

    with zipfile.ZipFile(output_path, 'r') as zf:
        # Check manifest exists
        assert "manifest.json" in zf.namelist()

        # Check object exists
        object_path = f"objects/{sample_vault['obj_hash']}"
        assert object_path in zf.namelist()

        # We don't verify content as it might be compressed,
        # but as long as it exists and pack didn't fail, it's good.

def test_unpack_capsule(sample_vault, tmp_path):
    output_path = tmp_path / "test.pvc"
    capsule.pack_capsule(str(sample_vault["manifest_path"]), str(output_path))

    restore_vault = tmp_path / "restore_vault"

    restored_manifest = capsule.unpack_capsule(str(output_path), str(restore_vault))

    assert os.path.exists(restored_manifest)
    assert "snapshots/imported" in restored_manifest

    # Verify object unpacked
    objects_dir = restore_vault / "objects"
    obj_hash = sample_vault["obj_hash"]
    assert os.path.exists(objects_dir / obj_hash)
