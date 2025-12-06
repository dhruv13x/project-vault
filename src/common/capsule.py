# src/common/capsule.py

import os
import zipfile
import json
import shutil
from typing import Optional
from src.common import manifest, cas

def pack_capsule(manifest_path: str, output_path: str) -> str:
    """
    Packs a snapshot (manifest + objects) into a .pvc capsule (ZIP archive).

    Args:
        manifest_path: Path to the manifest.json to export.
        output_path: Destination path for the .pvc file.

    Returns:
        The absolute path to the created capsule.
    """
    manifest_path = os.path.abspath(manifest_path)
    output_path = os.path.abspath(output_path)

    # Load manifest to find objects
    snapshot_data = manifest.load_manifest(manifest_path)

    # Locate vault root (assume standard structure)
    # manifest is usually in vault/snapshots/<project>/manifest.json
    manifest_dir = os.path.dirname(manifest_path)
    vault_root = os.path.dirname(os.path.dirname(manifest_dir))
    objects_dir = os.path.join(vault_root, "objects")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Add Manifest as 'manifest.json' at root of zip
        zf.write(manifest_path, arcname="manifest.json")

        # 2. Add referenced objects
        files = snapshot_data.get("files", {})
        added_objects = set()

        for file_entry in files.values():
            # Support both V1 (string hash) and V2 (dict)
            file_hash = None
            if isinstance(file_entry, str):
                file_hash = file_entry
            else:
                if file_entry.get("type", "file") == "file":
                    file_hash = file_entry.get("hash")

            if file_hash and file_hash not in added_objects:
                object_path = os.path.join(objects_dir, file_hash)
                if os.path.exists(object_path):
                    # Store in objects/HASH inside zip
                    zf.write(object_path, arcname=f"objects/{file_hash}")
                    added_objects.add(file_hash)
                else:
                    print(f"Warning: Object {file_hash} missing, skipping.")

    return output_path

def unpack_capsule(capsule_path: str, dest_vault_path: str) -> str:
    """
    Unpacks a .pvc capsule into a destination vault.

    Args:
        capsule_path: Path to the .pvc file.
        dest_vault_path: Path to the vault where contents should be imported.

    Returns:
        The path to the imported manifest file in the destination vault.
    """
    capsule_path = os.path.abspath(capsule_path)
    dest_vault_path = os.path.abspath(dest_vault_path)

    objects_dir = os.path.join(dest_vault_path, "objects")
    os.makedirs(objects_dir, exist_ok=True)

    snapshots_dir = os.path.join(dest_vault_path, "snapshots", "imported")
    os.makedirs(snapshots_dir, exist_ok=True)

    with zipfile.ZipFile(capsule_path, 'r') as zf:
        # Extract manifest first to read it
        manifest_content = zf.read("manifest.json")
        snapshot_data = json.loads(manifest_content)

        # Save manifest to local vault
        # We might want to rename it to avoid collisions or keep original name?
        # manifest.save_manifest generates name based on timestamp.
        # But here we have the exact data.
        manifest_path = manifest.save_manifest(snapshot_data, os.path.join(dest_vault_path, "snapshots"), project_name="imported")

        # Extract objects
        for member in zf.namelist():
            if member.startswith("objects/") and not member.endswith("/"):
                # It is an object file
                file_hash = os.path.basename(member)
                target_path = os.path.join(objects_dir, file_hash)

                # Check if exists to avoid overwrite (optimization)
                if not os.path.exists(target_path):
                    with zf.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)

    return manifest_path
