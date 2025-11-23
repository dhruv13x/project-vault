import os
import sys
import shutil
from src.common import manifest

def restore_snapshot(manifest_path: str, destination_path: str) -> None:
    """
    Restores a project snapshot from the vault to the destination path.
    
    Implements zero-trust validation to ensure that the paths in the manifest
    do not attempt directory traversal or absolute path writes.

    Args:
        manifest_path: Path to the snapshot manifest file.
        destination_path: Directory where the project should be restored.
    """
    # --- Safety Check: Prevent recursion/overwrite ---
    abs_manifest_path = os.path.abspath(manifest_path)
    abs_destination_path = os.path.abspath(destination_path)
    
    # vault_root is up two levels from manifest (snapshots/manifest.json -> snapshots -> vault)
    vault_root = os.path.dirname(os.path.dirname(abs_manifest_path))
    
    # Check for overlap using os.path.commonpath
    # We check if dest is inside vault OR vault is inside dest
    try:
        # commonpath raises ValueError if paths are on different drives (Windows)
        # or if strict validation fails.
        
        # Case 1: Dest is inside Vault (e.g., restoring to vault/restored)
        if os.path.commonpath([vault_root, abs_destination_path]) == vault_root:
            print("❌ SAFETY ERROR: Cannot restore into the Vault itself!")
            print(f"   Vault: {vault_root}")
            print(f"   Dest:  {abs_destination_path}")
            raise ValueError("Destination path is inside the Vault.")

        # Case 2: Vault is inside Dest (e.g., restoring to /, and vault is at /vault)
        # This is dangerous because we might overwrite the vault objects while restoring!
        if os.path.commonpath([vault_root, abs_destination_path]) == abs_destination_path:
            print("❌ SAFETY ERROR: The Vault is inside the restoration destination!")
            print("   This could lead to overwriting the vault itself.")
            print(f"   Vault: {vault_root}")
            print(f"   Dest:  {abs_destination_path}")
            raise ValueError("Vault path is inside the Destination path.")

    except ValueError as e:
        # Re-raise safety errors
        if "Vault" in str(e):
            raise
        # Ignore other commonpath errors (e.g. diff drives) as that implies safety
        pass


    print(f"Loading manifest from: {manifest_path}")
    try:
        snapshot_data = manifest.load_manifest(manifest_path)
    except Exception as e:
        print(f"Failed to load manifest: {e}")
        sys.exit(1)

    # Derive objects directory path
    # Manifests are stored in vault/snapshots/
    # Objects are stored in vault/objects/
    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    objects_dir = os.path.abspath(os.path.join(manifest_dir, "../objects"))

    if not os.path.exists(objects_dir):
        print(f"Error: Objects directory not found at {objects_dir}")
        sys.exit(1)

    print(f"Restoring to: {destination_path}")
    os.makedirs(destination_path, exist_ok=True)

    files = snapshot_data.get("files", {})
    restored_count = 0
    skipped_count = 0

    for rel_path, file_hash in files.items():
        # Zero-Trust Validation
        # 1. Check for absolute paths
        if os.path.isabs(rel_path):
            print(f"WARNING: Skipping absolute path '{rel_path}' (security risk)")
            skipped_count += 1
            continue
        
        # 2. Check for traversal attempts
        # Using os.path.normpath and checking if it starts with '..' is a robust check
        # providing the path is relative.
        normalized_path = os.path.normpath(rel_path)
        if normalized_path.startswith("..") or ".." in normalized_path.split(os.sep):
             print(f"WARNING: Skipping traversal path '{rel_path}' (security risk)")
             skipped_count += 1
             continue

        # Construct source and destination paths
        object_source = os.path.join(objects_dir, file_hash)
        file_dest = os.path.join(destination_path, rel_path)
        
        # Verify the object exists
        if not os.path.exists(object_source):
             print(f"ERROR: Missing object {file_hash} for file {rel_path}")
             # Depending on policy, we might want to abort or continue.
             # Continuing allows partial recovery.
             skipped_count += 1
             continue

        try:
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(file_dest), exist_ok=True)
            
            # Copy the file
            shutil.copy2(object_source, file_dest)
            print(f"Restoring: {rel_path}")
            restored_count += 1
            
        except Exception as e:
            print(f"Failed to restore {rel_path}: {e}")
            skipped_count += 1

    print(f"Restore complete. Restored: {restored_count}, Skipped/Failed: {skipped_count}")
