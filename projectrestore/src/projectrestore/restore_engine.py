import sys
import os
import shutil

# Path setup to allow importing from the shared 'src/common' directory.
# We are in projectrestore/src/projectrestore/
# We need to reach src/ (which sits at the repository root)
current_dir = os.path.dirname(os.path.abspath(__file__))
# ../../../src resolves to project_vault/src
shared_src_path = os.path.abspath(os.path.join(current_dir, "../../../src"))

if shared_src_path not in sys.path:
    sys.path.append(shared_src_path)

try:
    from common import manifest
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import shared modules 'common' from '{shared_src_path}'.")
    print(f"Details: {e}")
    print("Ensure that 'src/common' exists and has an __init__.py file.")
    sys.exit(1)

def restore_snapshot(manifest_path: str, destination_path: str) -> None:
    """
    Restores a project snapshot from the vault to the destination path.
    
    Implements zero-trust validation to ensure that the paths in the manifest
    do not attempt directory traversal or absolute path writes.

    Args:
        manifest_path: Path to the snapshot manifest file.
        destination_path: Directory where the project should be restored.
    """
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
