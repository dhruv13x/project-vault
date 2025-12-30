# projectclone/projectclone/status_engine.py

import os
import sys
import time
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import common modules
# We assume the orchestrator has set up sys.path correctly
try:
    from src.common import manifest, cas, ignore, b2, s3
except ImportError:
    # Fallback for direct execution or different path structures
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from src.common import manifest, cas, ignore, b2, s3

def _get_latest_snapshot(vault_path: str, project_name: str):
    """Finds the path to the latest snapshot manifest for a project."""
    snapshots_dir = os.path.join(vault_path, "snapshots", project_name)
    if not os.path.exists(snapshots_dir):
        return None

    files = sorted(
        [f for f in os.listdir(snapshots_dir) if f.endswith(".json")],
        reverse=True
    )
    if not files:
        return None
    return os.path.join(snapshots_dir, files[0])

def get_local_status(source_path: str, vault_path: str, project_name: str = None):
    """
    Analyzes the differences between the working directory and the latest local snapshot.
    """
    console = Console()
    
    abs_source = os.path.abspath(source_path)
    if project_name is None:
        project_name = os.path.basename(abs_source)
        # Sanitize as per cas_engine
        project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)

    # 1. Find Latest Snapshot
    latest_manifest_path = _get_latest_snapshot(vault_path, project_name)
    
    status_data = {
        "project": project_name,
        "snapshot_exists": False,
        "snapshot_time": None,
        "new_files": [],
        "modified_files": [],
        "deleted_files": [],
        "total_scanned": 0
    }

    manifest_files = {}
    if latest_manifest_path:
        try:
            data = manifest.load_manifest(latest_manifest_path)
            manifest_files = data.get("files", {})
            status_data["snapshot_exists"] = True
            status_data["snapshot_time"] = data.get("timestamp")
        except Exception as e:
            console.print(f"[red]Error loading manifest:[/red] {e}")
            return status_data

    # 2. Scan Working Directory
    # Load ignore patterns
    ignore_patterns = ['.git', '__pycache__', '.DS_Store', '.vaultignore']
    vaultignore_path = os.path.join(source_path, ".vaultignore")
    if os.path.exists(vaultignore_path):
        ignore_patterns.extend(ignore.parse_ignore_file(vaultignore_path))

    scanned_files = set()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Scanning workspace...", total=None)

        for root, dirs, files in os.walk(source_path):
            # Prune ignored directories
            for i in range(len(dirs) - 1, -1, -1):
                d = dirs[i]
                dir_full_path = os.path.join(root, d)
                if ignore.should_ignore(dir_full_path, ignore_patterns, source_path):
                    del dirs[i]

            for file in files:
                full_path = os.path.join(root, file)
                if ignore.should_ignore(full_path, ignore_patterns, source_path):
                    continue

                rel_path = os.path.relpath(full_path, source_path)
                scanned_files.add(rel_path)
                status_data["total_scanned"] += 1

                # Check status
                if rel_path not in manifest_files:
                    status_data["new_files"].append(rel_path)
                else:
                    # Compare content
                    # Optimization: We assume hash calculation is needed since we don't store size/mtime yet.
                    # This might be slow for large files.
                    try:
                        current_hash = cas.calculate_hash(full_path)
                        if current_hash != manifest_files[rel_path]:
                            status_data["modified_files"].append(rel_path)
                    except OSError:
                        # File might have vanished during scan
                        pass

    # 3. Detect Deleted Files
    for rel_path in manifest_files:
        if rel_path not in scanned_files:
            status_data["deleted_files"].append(rel_path)

    return status_data

def get_cloud_status(vault_path: str, bucket: str, endpoint: str, key_id: str, app_key: str):
    """
    Compares local snapshots with cloud snapshots.
    """
    status = {
        "connected": False,
        "error": None,
        "local_count": 0,
        "cloud_count": 0,
        "to_push": 0,
        "to_pull": 0,
        "synced": False
    }

    try:
        # Setup Manager
        if endpoint or os.environ.get("AWS_ACCESS_KEY_ID"):
            manager = s3.S3Manager(key_id, app_key, bucket, endpoint)
        else:
            manager = b2.B2Manager(key_id, app_key, bucket)
        
        status["connected"] = True

        # Fetch Cloud List
        cloud_files = set(manager.list_file_names())
        
        # Identify Snapshots
        cloud_snapshots = {f for f in cloud_files if f.startswith("snapshots/") and f.endswith(".json")}
        status["cloud_count"] = len(cloud_snapshots)

        # Identify Local Snapshots
        local_snapshots = set()
        snapshots_dir = os.path.join(vault_path, "snapshots")
        if os.path.exists(snapshots_dir):
            for root, _, files in os.walk(snapshots_dir):
                for f in files:
                    if f.endswith(".json"):
                        # Reconstruct key: snapshots/<project>/<filename>
                        rel_path = os.path.relpath(os.path.join(root, f), snapshots_dir)
                        key = f"snapshots/{rel_path}".replace(os.sep, "/")
                        local_snapshots.add(key)
        
        status["local_count"] = len(local_snapshots)
        
        # Diff
        status["local_only"] = local_snapshots - cloud_snapshots
        status["cloud_only"] = cloud_snapshots - local_snapshots
        status["to_push"] = len(status["local_only"])
        status["to_pull"] = len(status["cloud_only"])
        status["synced"] = (status["to_push"] == 0 and status["to_pull"] == 0)

    except Exception as e:
        status["error"] = str(e)

    return status

def show_status(source_path, vault_path, cloud_config=None):
    console = Console()
    
    abs_source = os.path.abspath(source_path)
    abs_vault = os.path.abspath(vault_path)

    # --- Safety Checks ---
    if abs_source == abs_vault:
        console.print("[bold red]⛔ Error: Source and Vault paths cannot be the same.[/bold red]")
        console.print("   Using the source directory as the vault causes infinite recursion and data corruption.")
        return

    # Check nesting
    if abs_vault.startswith(abs_source) and (
        len(abs_vault) == len(abs_source) or abs_vault[len(abs_source)] == os.sep
    ):
        # Check if ignored
        rel_vault = os.path.relpath(abs_vault, abs_source)
        
        # Load ignores to check
        ignore_patterns = ['.git', '__pycache__', '.DS_Store', '.vaultignore']
        pvignore_path = os.path.join(source_path, ".pvignore")
        if os.path.exists(pvignore_path):
            ignore_patterns.extend(ignore.parse_ignore_file(pvignore_path))
        
        # We use a simple check here or reuse scanner logic. 
        # scanner.matches_excludes is robust.
        from src.projectclone.scanner import matches_excludes, get_project_ignore_spec
        
        # We need to check if the VAULT folder itself is ignored.
        # matches_excludes checks against ignore_spec.
        spec = get_project_ignore_spec(Path(source_path))
        
        # Also check standard ignores list manually if not in spec?
        # get_project_ignore_spec handles .pvignore. 
        # We should also pass the default system ignores if we want to be consistent, 
        # but usually vault isn't .git.
        
        # matches_excludes expects an absolute path (or one resolvable to inside root)
        # We already have abs_vault.
        
        # We explicitly check if the vault path matches the ignore spec.
        # Note: matches_excludes resolves paths.
        if not matches_excludes(Path(abs_vault), root=Path(source_path), ignore_spec=spec):
             console.print("[bold red]⛔ Error: Vault path is inside Source path but not ignored.[/bold red]")

    # Header
    console.print(Panel.fit(
        f"[bold blue]Project Vault Status[/bold blue]\n"
        f"Source: [yellow]{source_path}[/yellow]\n"
        f"Vault:  [yellow]{vault_path}[/yellow]"
    ))

    # --- Local Status ---
    console.print("\n[bold underline]Local Workspace[/bold underline]")
    
    if not os.path.exists(vault_path):
        console.print("[red]Vault path does not exist![/red]")
        return

    local_stat = get_local_status(source_path, vault_path)
    
    if not local_stat["snapshot_exists"]:
        console.print("[yellow]No snapshots found for this project.[/yellow]")
        console.print(f"  Found {local_stat['total_scanned']} files ready to back up.")
    else:
        ts = local_stat["snapshot_time"]
        console.print(f"Latest Snapshot: [green]{ts}[/green]")
        
        # Diff Table
        changes = len(local_stat["new_files"]) + len(local_stat["modified_files"]) + len(local_stat["deleted_files"])
        
        if changes == 0:
            console.print("[bold green]✔ Workspace is clean (matches latest snapshot)[/bold green]")
        else:
            console.print(f"[bold red]⚠ Workspace has {changes} pending changes[/bold red]")
            
            table = Table(show_header=True, header_style="bold white")
            table.add_column("Type", width=12)
            table.add_column("File")
            
            # Limit output to prevent flooding
            max_rows = 10
            count = 0
            
            for f in local_stat["modified_files"]:
                if count >= max_rows: break
                table.add_row("[yellow]Modified[/yellow]", f)
                count += 1
            for f in local_stat["new_files"]:
                if count >= max_rows: break
                table.add_row("[green]New[/green]", f)
                count += 1
            for f in local_stat["deleted_files"]:
                if count >= max_rows: break
                table.add_row("[red]Deleted[/red]", f)
                count += 1
                
            console.print(table)
            if changes > max_rows:
                console.print(f"[dim]...and {changes - max_rows} more.[/dim]")
            
            console.print("\n[bold]Suggestion:[/bold] Run [cyan]pv vault[/cyan] to snapshot these changes.")

    # --- Cloud Status ---
    if cloud_config and cloud_config.get("bucket"):
        console.print("\n[bold underline]Cloud Sync[/bold underline]")
        
        if not cloud_config.get("key_id"):
            console.print("[dim]Cloud credentials not set. Skipping check.[/dim]")
        else:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                progress.add_task("[magenta]Checking cloud status...", total=None)
                cloud_stat = get_cloud_status(
                    vault_path,
                    cloud_config["bucket"],
                    cloud_config.get("endpoint"),
                    cloud_config["key_id"],
                    cloud_config["app_key"]
                )

            if cloud_stat["error"]:
                console.print(f"[red]Error connecting to cloud:[/red] {cloud_stat['error']}")
            else:
                console.print(f"Target: [cyan]{cloud_config['bucket']}[/cyan]")
                
                if cloud_stat["synced"]:
                    console.print("✅ [bold green]Local vault is fully synchronized with cloud.[/bold green]")
                else:
                    # Use a table or list showing which snapshots need pushing/pulling.
                    if cloud_stat["to_push"] > 0:
                        console.print(f"[yellow]⚠ Local is ahead by {cloud_stat['to_push']} snapshots (Run 'pv push')[/yellow]")
                    if cloud_stat["to_pull"] > 0:
                        console.print(f"[yellow]⚠ Remote is ahead by {cloud_stat['to_pull']} snapshots (Run 'pv pull')[/yellow]")

                    # Detailed Table
                    table = Table(show_header=True, header_style="bold white", title="Sync Differences")
                    table.add_column("Action", width=12)
                    table.add_column("Snapshot")

                    max_rows = 15
                    count = 0

                    # Sort for consistent display
                    local_only = sorted(list(cloud_stat.get("local_only", [])))
                    cloud_only = sorted(list(cloud_stat.get("cloud_only", [])))

                    for f in local_only:
                        if count >= max_rows: break
                        table.add_row("[green]Push (Local)[/green]", f)
                        count += 1

                    for f in cloud_only:
                        if count >= max_rows: break
                        table.add_row("[blue]Pull (Remote)[/blue]", f)
                        count += 1

                    console.print(table)
                    if (len(local_only) + len(cloud_only)) > max_rows:
                        console.print(f"[dim]...and more.[/dim]")

                # Warning if the latest local snapshot is not in the cloud
                # We need to find the latest local snapshot first.
                # get_local_status does finding latest snapshot but we don't return the filename there easily.
                # But here we have the vault_path.
                # We can check if the latest snapshot for the current project is in "local_only".

                # Infer project name from source path or vault structure?
                # Usually vault is organized by project.
                # But here we might be checking status of a specific project workspace.
                # get_local_status derived project_name from source_path.
                # Let's derive it again here to check.

                project_name = os.path.basename(os.path.abspath(source_path))
                # Sanitize as per cas_engine
                project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)

                latest = _get_latest_snapshot(vault_path, project_name)
                if latest:
                    # "snapshots/project_name/timestamp.json"
                    rel_path = os.path.relpath(latest, os.path.join(vault_path, "snapshots"))
                    key = f"snapshots/{rel_path}".replace(os.sep, "/")

                    # cloud_stat["local_only"] contains keys that are NOT in cloud.
                    if key in cloud_stat.get("local_only", set()):
                         console.print(f"[bold red]🚨 Warning: The latest snapshot ({os.path.basename(key)}) is NOT in the cloud![/bold red]")
                         console.print("   Your latest work is not protected off-site. Run [bold white]pv push[/bold white] immediately.")
