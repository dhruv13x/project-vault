#!/usr/bin/env python3
# src/projectclone/list_engine.py

"""
Provides functions to list local and cloud-based snapshots.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from pv_core import b2


def _parse_snapshot_name(filename: str) -> str:
    """
    Parses a snapshot filename to extract a human-readable timestamp.

    Args:
        filename: The snapshot filename (e.g., "snapshot_2025-11-22T15-12-01.570822+00-00.json")

    Returns:
        A formatted string (e.g., "2025-11-22 15:12:01") or the original filename on failure.
    """
    try:
        # Assumes format: "snapshot_YYYY-MM-DDTHH-MM-SS.micros+timezone.json"
        base = filename.split('_', 1)[1]
        timestamp_part = base.split('.')[0]
        
        date_part, time_part = timestamp_part.split('T')
        time_part_fixed = time_part.replace('-', ':')
        
        parsable_timestamp = f"{date_part}T{time_part_fixed}"
        
        dt = datetime.fromisoformat(parsable_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (IndexError, ValueError):
        # Handle cases where the format might vary or be unexpected
        return filename


def list_local_snapshots(vault_path: str):
    """
    Scans a local vault path and lists all found snapshots in a table.
    """
    console = Console()
    vault_p = Path(vault_path)
    snapshots_dir = vault_p / "snapshots"

    if not snapshots_dir.is_dir():
        console.print(f"[bold red]Error:[/bold red] Snapshot directory not found at: {snapshots_dir}")
        return

    table = Table(title="Local Vault Snapshots", show_header=True, header_style="bold magenta")
    table.add_column("Project", style="cyan", no_wrap=True)
    table.add_column("Snapshot Time", style="green")
    table.add_column("Manifest File", style="dim")

    found_any = False
    for project_dir in sorted(snapshots_dir.iterdir()):
        if project_dir.is_dir():
            project_name = project_dir.name
            # Find all .json files and sort them newest first
            manifests = sorted(
                [f for f in project_dir.glob("*.json") if f.is_file()],
                key=lambda p: p.name,
                reverse=True
            )
            for manifest_path in manifests:
                found_any = True
                pretty_time = _parse_snapshot_name(manifest_path.name)
                table.add_row(project_name, pretty_time, manifest_path.name)
    
    if not found_any:
        console.print(f"No snapshots found in {snapshots_dir}")
    else:
        console.print(table)


def list_cloud_snapshots(bucket_name: str, key_id: str, app_key: str, endpoint: str = None):
    """
    Connects to a Cloud bucket (S3 or B2) and lists all found snapshots.
    """
    console = Console()
    table = Table(title=f"Cloud Snapshots in Bucket: '{bucket_name}'", show_header=True, header_style="bold magenta")
    table.add_column("Project", style="cyan", no_wrap=True)
    table.add_column("Snapshot Time", style="green")
    table.add_column("Manifest File", style="dim")

    try:
        # Logic: If an endpoint is provided OR we have AWS credentials in env, prefer S3.
        # Otherwise, default to B2 Native.
        if endpoint or os.environ.get("AWS_ACCESS_KEY_ID"):
             from pv_core import s3
             manager = s3.S3Manager(key_id, app_key, bucket_name, endpoint)
        else:
             from pv_core import b2
             manager = b2.B2Manager(key_id, app_key, bucket_name)

        console.print("Fetching snapshot list from Cloud...")
        cloud_files = manager.list_file_names()

        snapshot_prefix = "snapshots/"
        projects = {}

        for file_name in cloud_files:
            if file_name.startswith(snapshot_prefix) and file_name.endswith(".json"):
                parts = file_name.split('/')
                # Expected structure: snapshots/<project_name>/<filename>.json
                if len(parts) == 3:
                    project_name = parts[1]
                    manifest_name = parts[2]
                    if project_name not in projects:
                        projects[project_name] = []
                    projects[project_name].append(manifest_name)

        if not projects:
            console.print("No snapshots found in the cloud bucket.")
            return
            
        for project_name in sorted(projects.keys()):
            manifests = sorted(projects[project_name], reverse=True)
            for manifest_name in manifests:
                pretty_time = _parse_snapshot_name(manifest_name)
                table.add_row(project_name, pretty_time, manifest_name)

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error connecting to cloud backend:[/bold red] {e}")

if __name__ == '__main__':
    # Example Usage (requires a local vault structure to exist)
    # To test, you would need a vault at '/path/to/your/vault'
    # with a structure like:
    # /path/to/your/vault/snapshots/my-project/snapshot_2025-11-23T10-00-00.json
    
    print("--- Listing local snapshots ---")
    # Replace with the actual path to your vault for testing
    local_vault_path = os.getenv("PV_VAULT_PATH", "./.vault") 
    list_local_snapshots(local_vault_path)

    print("\n--- Listing cloud snapshots ---")
    # To test, set these environment variables with your B2 credentials
    b2_bucket = os.getenv("B2_BUCKET")
    b2_key_id = os.getenv("B2_KEY_ID")
    b2_app_key = os.getenv("B2_APP_KEY")

    if b2_bucket and b2_key_id and b2_app_key:
        list_cloud_snapshots(b2_bucket, b2_key_id, b2_app_key)
    else:
        print("Skipping cloud snapshot listing.")
        print("Set B2_BUCKET, B2_KEY_ID, and B2_APP_KEY environment variables to test.")