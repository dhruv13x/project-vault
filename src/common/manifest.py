# src/common/manifest.py

import json
import os
import platform
import socket
from datetime import datetime, timezone
from typing import Dict, Any

MANIFEST_VERSION = 2

def create_snapshot_structure(source_path: str) -> Dict[str, Any]:
    """
    Creates the initial structure for a snapshot manifest.

    Args:
        source_path: The absolute path of the source directory being backed up.

    Returns:
        A dictionary containing the timestamp, absolute source path, empty files dictionary,
        and manifest version.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": MANIFEST_VERSION,
        "timestamp": now,
        "created_at": now,
        "source_path": os.path.abspath(source_path),
        "source_os": platform.system(),
        "hostname": socket.gethostname(),
        "files": {}
    }

def save_manifest(snapshot_data: Dict[str, Any], snapshots_dir: str, project_name: str = "default") -> str:
    """
    Saves the snapshot data as a pretty-printed JSON file.

    The filename is generated based on the timestamp found in snapshot_data.
    Colons in the timestamp are replaced with hyphens to ensure filesystem compatibility.
    Snapshots are organized into subdirectories by project_name.

    Args:
        snapshot_data: The dictionary containing snapshot details.
        snapshots_dir: The root directory where snapshots are stored.
        project_name: The name of the project (used for subdirectory organization).

    Returns:
        The absolute path to the saved manifest file.
    """
    target_dir = os.path.join(snapshots_dir, project_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Sanitize timestamp for filename usage (replace colons with hyphens)
    safe_timestamp = snapshot_data["timestamp"].replace(":", "-")
    filename = f"snapshot_{safe_timestamp}.json"
    file_path = os.path.join(target_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, indent=4)

    return os.path.abspath(file_path)

def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """
    Reads and returns the content of a manifest JSON file.

    Args:
        manifest_path: The path to the manifest file.

    Returns:
        The dictionary content of the manifest.
    """
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)
