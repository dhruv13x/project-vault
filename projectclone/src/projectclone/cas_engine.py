import sys
import os

# Path setup to allow importing from the shared 'src/common' directory.
# We are currently in projectclone/src/projectclone/
# We need to reach src/ (which sits at the repository root)
current_dir = os.path.dirname(os.path.abspath(__file__))
# ../../../src resolves to project_vault/src
shared_src_path = os.path.abspath(os.path.join(current_dir, "../../../src"))

if shared_src_path not in sys.path:
    sys.path.append(shared_src_path)

try:
    from common import cas, manifest
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import shared modules 'common' from '{shared_src_path}'.")
    print(f"Details: {e}")
    print("Ensure that 'src/common' exists and has an __init__.py file.")
    sys.exit(1)


def backup_to_vault(source_path: str, vault_path: str) -> str:
    """
    Performs a content-addressable backup of the source path to the vault.

    Args:
        source_path: The directory to back up.
        vault_path: The root directory of the backup vault.

    Returns:
        The absolute path to the saved manifest file.
    """
    # Initialize the snapshot structure
    snapshot_data = manifest.create_snapshot_structure(source_path)
    
    objects_dir = os.path.join(vault_path, "objects")
    snapshots_dir = os.path.join(vault_path, "snapshots")

    print(f"Starting backup of '{source_path}' to '{vault_path}'...")

    # Walk through the source directory
    for root, _, files in os.walk(source_path):
        for file in files:
            full_path = os.path.join(root, file)
            
            # Calculate relative path for the manifest
            rel_path = os.path.relpath(full_path, source_path)
            
            try:
                # Store the object (deduplicated) and get its hash
                file_hash = cas.store_object(full_path, objects_dir)
                
                # Record in manifest
                snapshot_data["files"][rel_path] = file_hash
                
                print(f"Hashed: {rel_path} -> {file_hash}")
                
            except Exception as e:
                print(f"Error processing {rel_path}: {e}")
                # We might want to raise here or continue depending on policy.
                # For now, we print and re-raise to ensure integrity.
                raise

    # Save the manifest
    manifest_path = manifest.save_manifest(snapshot_data, snapshots_dir)
    print(f"Backup complete. Manifest saved to: {manifest_path}")
    
    return manifest_path
