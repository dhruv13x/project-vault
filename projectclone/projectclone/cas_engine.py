import sys
import os
from src.common import cas, manifest, ignore


def backup_to_vault(source_path: str, vault_path: str, project_name: str = None) -> str:
    """
    Performs a content-addressable backup of the source path to the vault.

    Args:
        source_path: The directory to back up.
        vault_path: The root directory of the backup vault.
        project_name: The name of the project. If None, it is derived from the source path.

    Returns:
        The absolute path to the saved manifest file.
    """
    # --- Safety Checks ---
    abs_source = os.path.abspath(source_path)
    abs_vault = os.path.abspath(vault_path)

    # Check 1: Identity
    if abs_source == abs_vault:
        print("❌ SAFETY ERROR: Source and Vault paths cannot be the same.")
        raise ValueError("Source and Vault paths cannot be the same.")

    # Check 2: Nesting (Vault inside Source)
    if abs_vault.startswith(abs_source) and (
        len(abs_vault) == len(abs_source) or abs_vault[len(abs_source)] == os.sep
    ):
        ignore_patterns = ['.git', '__pycache__', '.DS_Store', '.vaultignore']
        vaultignore_path = os.path.join(source_path, ".vaultignore")
        if os.path.exists(vaultignore_path):
            ignore_patterns.extend(ignore.parse_ignore_file(vaultignore_path))
            
        if not ignore.should_ignore(abs_vault, ignore_patterns, abs_source):
             print("❌ SAFETY ERROR: Vault path is inside Source path but not ignored.")
             print("   This causes infinite recursion (backing up the backup).")
             print(f"   Source: {abs_source}")
             print(f"   Vault:  {abs_vault}")
             print("   Fix: Add the vault directory to .vaultignore or move the vault outside.")
             raise ValueError("Vault path is inside Source path but not ignored.")

    # --- Project Name Handling ---
    if project_name is None:
        project_name = os.path.basename(abs_source)
    
    # Simple sanitization (replace spaces, strip non-alphanumeric except -_)
    # This regex keeps alphanumeric, underscores, and hyphens.
    import re
    safe_project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
    
    print(f"Using project name: {safe_project_name}")

    # Initialize the snapshot structure
    snapshot_data = manifest.create_snapshot_structure(source_path)
    
    objects_dir = os.path.join(vault_path, "objects")
    snapshots_dir = os.path.join(vault_path, "snapshots")
    
    # Load ignore patterns
    ignore_patterns = ['.git', '__pycache__', '.DS_Store', '.vaultignore']
    vaultignore_path = os.path.join(source_path, ".vaultignore")
    if os.path.exists(vaultignore_path):
        ignore_patterns.extend(ignore.parse_ignore_file(vaultignore_path))

    print(f"Starting backup of '{source_path}' to '{vault_path}'...")

    # Walk through the source directory
    for root, dirs, files in os.walk(source_path):
        # Prune ignored directories
        for i in range(len(dirs) - 1, -1, -1):
            d = dirs[i]
            dir_full_path = os.path.join(root, d)
            if ignore.should_ignore(dir_full_path, ignore_patterns, source_path):
                print(f"Skipped directory: {os.path.relpath(dir_full_path, source_path)}")
                del dirs[i]

        for file in files:
            full_path = os.path.join(root, file)
            if ignore.should_ignore(full_path, ignore_patterns, source_path):
                print(f"Skipped file: {os.path.relpath(full_path, source_path)}")
                continue

            rel_path = os.path.relpath(full_path, source_path)
            try:
                file_hash = cas.store_object(full_path, objects_dir)
                snapshot_data["files"][rel_path] = file_hash
                print(f"Hashed: {rel_path} -> {file_hash}")
            except Exception as e:
                print(f"Error processing {rel_path}: {e}")
                raise

    # Save the manifest
    manifest_path = manifest.save_manifest(snapshot_data, snapshots_dir, project_name=safe_project_name)
    print(f"Backup complete. Manifest saved to: {manifest_path}")
    
    return manifest_path
