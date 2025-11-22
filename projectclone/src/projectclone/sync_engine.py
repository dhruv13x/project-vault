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
    from common import b2
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import shared modules 'common' from '{shared_src_path}'.")
    print(f"Details: {e}")
    print("Ensure that 'src/common' exists and has an __init__.py file.")
    sys.exit(1)


def sync_to_cloud(vault_path: str, bucket_name: str, endpoint: str, key_id: str, app_key: str):
    """
    Syncs the local vault content (objects and snapshots) to a Backblaze B2 bucket.
    
    Args:
        vault_path: Path to the local vault directory.
        bucket_name: Name of the target B2 bucket.
        endpoint: (Ignored) Kept for CLI compatibility.
        key_id: B2 Key ID.
        app_key: B2 App Key.
    """
    print(f"Connecting to B2 bucket: {bucket_name}...")
    manager = b2.B2Manager(key_id, app_key, bucket_name)
    
    print("Fetching file list from B2...")
    remote_files = manager.list_file_names()
    print(f"Found {len(remote_files)} existing files in cloud.")
    
    # --- Phase 1: Sync Objects ---
    local_objects_dir = os.path.join(vault_path, "objects")
    if os.path.exists(local_objects_dir):
        for root, _, files in os.walk(local_objects_dir):
            for file in files:
                local_path = os.path.join(root, file)
                # Remote key structure: objects/<hash>
                remote_key = f"objects/{file}"
                
                if remote_key in remote_files:
                    print(f"Skipping object: {file} (Exists)")
                else:
                    # Uploading happens inside manager.upload_file which prints progress
                    manager.upload_file(local_path, remote_key)
    else:
        print(f"No objects directory found at {local_objects_dir}")

    # --- Phase 2: Sync Snapshots ---
    local_snapshots_dir = os.path.join(vault_path, "snapshots")
    if os.path.exists(local_snapshots_dir):
        for root, _, files in os.walk(local_snapshots_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue
                
                local_path = os.path.join(root, file)
                remote_key = f"snapshots/{file}"
                
                if remote_key in remote_files:
                    print(f"Skipping snapshot: {file} (Exists)")
                else:
                    manager.upload_file(local_path, remote_key)
    else:
        print(f"No snapshots directory found at {local_snapshots_dir}")

    print("Cloud sync complete.")


def sync_from_cloud(vault_path: str, bucket_name: str, endpoint: str, key_id: str, app_key: str):
    """
    Syncs the local vault content (objects and snapshots) FROM a Backblaze B2 bucket.
    Downloads any objects or snapshots that are missing locally.
    
    Args:
        vault_path: Path to the local vault directory.
        bucket_name: Name of the source B2 bucket.
        endpoint: (Ignored) Kept for CLI compatibility.
        key_id: B2 Key ID.
        app_key: B2 App Key.
    """
    print(f"Connecting to B2 bucket: {bucket_name}...")
    manager = b2.B2Manager(key_id, app_key, bucket_name)
    
    print("Fetching file list from B2...")
    remote_files = manager.list_file_names()
    print(f"Found {len(remote_files)} files in cloud.")

    # --- Phase 1: Sync Objects (Cloud -> Local) ---
    print("Syncing objects from cloud...")
    for remote_file in remote_files:
        if remote_file.startswith("objects/"):
            # Extract filename (hash) from remote path "objects/hash"
            filename = os.path.basename(remote_file)
            local_path = os.path.join(vault_path, "objects", filename)
            
            if os.path.exists(local_path):
                print(f"Skipping object: {filename} (Exists)")
            else:
                manager.download_file(remote_file, local_path)
        
        # --- Phase 2: Sync Snapshots (Cloud -> Local) ---
        elif remote_file.startswith("snapshots/") and remote_file.endswith(".json"):
            filename = os.path.basename(remote_file)
            local_path = os.path.join(vault_path, "snapshots", filename)
            
            if os.path.exists(local_path):
                print(f"Skipping snapshot: {filename} (Exists)")
            else:
                manager.download_file(remote_file, local_path)
    
    print("Cloud download complete.")