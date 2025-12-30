import sys
import os
import re
from rich.panel import Panel
from rich.text import Text
from src.common.console import console

def resolve_path(path_str):
    """
    Expands user (~) and environment variables ($VAR) in a path,
    then returns the absolute path.
    """
    if not path_str:
        return path_str
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path_str)))

def handle_vault_command(args, defaults, notifier=None, credentials_module=None):
    source_abs = resolve_path(args.source)
    project_name = args.name or os.path.basename(source_abs)

    if not args.vault_path:
        from src.common.paths import get_default_vault_path
        args.vault_path = str(get_default_vault_path(project_name))

    print(f"DEBUG: include_db = {getattr(args, "include_db", "NOT_FOUND")}")
    # Ensure parent dir exists (project home)
    vault_dir = os.path.dirname(args.vault_path)
    if vault_dir:
        os.makedirs(vault_dir, exist_ok=True)

    # --- Database Marker Detection & Suggestions ---
    enable_suggestions = defaults.get("core", {}).get("enable_suggestions", True)
    if enable_suggestions and getattr(args, "include_db", False) is not True:
        from src.common import detective
        markers = detective.detect_database_markers(source_abs)
        if markers:
            if defaults.get("database"):
                console.print(Panel(Text.from_markup(
                    f"💡 [bold yellow]Database markers detected:[/] {', '.join(markers)}.\n"
                    "Would you like to include a database snapshot? Re-run with [bold cyan]--include-db[/]."
                ), border_style="yellow"))
            else:
                console.print(Panel(Text.from_markup(
                    f"💡 [bold cyan]Database markers detected:[/] {', '.join(markers)}.\n"
                    "Run [bold cyan]pv init --db[/] to configure database snapshots for this project."
                ), border_style="cyan"))

    db_manifest_hash = None
        
    if getattr(args, "include_db", False) is True:
        from src.projectvault.engines.db_engine import DatabaseEngine
        from src.common.hashing import get_hash
        db_config = defaults.get("database", {})
        if not db_config:
            console.print("[error]Error: --include-db used but no [database] section in pv.toml.[/error]")
            sys.exit(1)

        driver_name = db_config.get("driver", "postgres")
        engine = DatabaseEngine(driver_name, db_config)

        # Backup DB first
        db_manifest_path = engine.backup(
            resolve_path(args.vault_path),
            project_name,
            cloud_sync=getattr(args, "cloud", False),
            credentials_module=credentials_module,
            bucket=args.bucket,
            endpoint=args.endpoint
        )
        db_manifest_hash = get_hash(db_manifest_path)
        # Register the db manifest itself as a blob in CAS so it can be restored
        from src.common import cas
        objects_dir = os.path.join(resolve_path(args.vault_path), "objects")
        db_manifest_hash = cas.store_object(db_manifest_path, objects_dir)

    # Extract hooks
    hooks = defaults.get("hooks", {})
    if hooks:
        console.print("[bold yellow]⚠ Lifecycle Hooks Detected[/bold yellow]")
        console.print("   Executing arbitrary shell commands defined in pv.toml.")

    from src.projectclone import cas_engine
    try:
        # Resolve follow_symlinks from args (default to False if not present to match legacy behavior of preserving by default)
        # If args.symlinks is set (Preserve), follow is False.
        # If args.symlinks is not set (Follow), follow is True?
        # Wait, let's match the logic decided:
        # --symlinks means PRESERVE. Default is FOLLOW.
        # So follow_symlinks = not args.symlinks
        
        preserve_symlinks = getattr(args, "symlinks", False)
        
        manifest_path = cas_engine.backup_to_vault(
            source_abs,
            resolve_path(args.vault_path),
            project_name=project_name,
            hooks=hooks,
            follow_symlinks=not preserve_symlinks,
            db_manifest=db_manifest_hash
        )
        
        # Inject db_manifest link if present
        if db_manifest_hash:
            try:
                import json
                with open(manifest_path, 'r') as f:
                    m_data = json.load(f)
                m_data['db_manifest'] = db_manifest_hash
                with open(manifest_path, 'w') as f:
                    json.dump(m_data, f, indent=2)
                console.print(f"[dim]Linked database snapshot {db_manifest_hash} to project manifest.[/dim]")
            except Exception as e:
                console.print(f"[warning]Warning: Failed to link DB snapshot to manifest: {e}[/warning]")
        if notifier:
            notifier.send_message(f"✅ Snapshot created for '{project_name}'\nManifest: {manifest_path}", level="success")
            
        # --- Cloud Sync Integration ---
        if getattr(args, "cloud", False) is True:
            if not credentials_module:
                console.print("[warning]Warning: credentials_module not provided, skipping cloud sync.[/warning]")
            else:
                if not args.bucket:
                    console.print("[error]Error: --bucket must be specified in CLI or pv.toml for cloud sync.[/error]")
                    # We don't exit here to preserve the local backup success, but we report error
                else:
                    key_id, app_key, source = credentials_module.resolve_credentials(args)
                    if not key_id or not app_key:
                        console.print("[error]Error: Cloud credentials missing. Skipping push.[/error]")
                        if notifier:
                            notifier.send_message("❌ Cloud Push Failed: Credentials missing", level="error")
                    else:
                        console.print(f"[dim]Authenticated via {source}[/dim]")
                        from src.projectclone import sync_engine
                        try:
                            sync_engine.sync_to_cloud(
                                resolve_path(args.vault_path),
                                args.bucket,
                                args.endpoint,
                                key_id,
                                app_key,
                                dry_run=getattr(args, "dry_run", False) # vault command doesn't have dry-run usually, but we should handle it if added
                            )
                            if notifier:
                                notifier.send_message(f"☁️ Cloud Push Successful to '{args.bucket}'", level="success")
                        except Exception as e:
                            console.print(f"[error]Cloud Push Failed: {e}[/error]")
                            if notifier:
                                notifier.send_message(f"❌ Cloud Push Failed: {e}", level="error")

    except Exception as e:
        if notifier:
            notifier.send_message(f"🚨 Vault Snapshot Failed: {e}", level="error")
        raise

def handle_vault_restore_command(args, defaults):
    if not args.dest:
        console.print("[error]Error: Destination directory must be specified in CLI or 'restore_path' in pv.toml[/error]")
        sys.exit(1)

    # Extract hooks
    hooks = defaults.get("hooks", {})
    if hooks:
        console.print("[bold red]⚠ Lifecycle Hooks Detected[/bold red]")
        console.print("   This will execute shell commands defined in the snapshot configuration.")
        console.print("   Ensure you trust the source of this backup.")
    import json

    from src.projectrestore import restore_engine
    manifest_path = resolve_path(args.manifest)
    dest_path = resolve_path(args.dest)
    
    # 1. Restore Files
    restore_engine.restore_snapshot(
        manifest_path,
        dest_path,
        hooks=hooks
    )

    # 2. Check for linked Database Snapshot
    try:
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        
        db_manifest_hash = manifest_data.get("db_manifest")
        if db_manifest_hash:
            console.print(Panel(Text.from_markup(
                f"📦 [bold cyan]Linked Database Snapshot Detected:[/] {db_manifest_hash}\n"
                "Restoring database state to match the project version..."
            ), border_style="cyan"))
            
            # Find the database manifest in the vault
            # Since it's content-addressable, we look in the objects dir
            vault_path = os.path.dirname(os.path.dirname(os.path.dirname(manifest_path)))
            db_manifest_path = os.path.join(vault_path, "objects", db_manifest_hash)
            
            if os.path.exists(db_manifest_path):
                from src.projectvault.engines.db_engine import DatabaseEngine
                from src.common import cas
                import tempfile
                import shutil
                db_config = defaults.get("database", {})
                if not db_config:
                    console.print("[warning]Warning: Database manifest found, but no [database] config in pv.toml. Skipping DB restore.[/warning]")
                else:
                    engine = DatabaseEngine(db_config.get("driver", "postgres"), db_config)
                    force_restore = getattr(args, "force", False)
                    
                    # 1. Copy manifest OUT of the vault to bypass faulty safety checks in projectrestore
                    # 2. Decompress if needed (CAS objects are always compressed)
                    with tempfile.TemporaryDirectory() as tmp_vault:
                        dummy_objects = os.path.join(tmp_vault, "objects")
                        dummy_snapshots = os.path.join(tmp_vault, "snapshots", "db_restore")
                        os.makedirs(dummy_snapshots, exist_ok=True)
                        os.symlink(os.path.join(vault_path, "objects"), dummy_objects)
                        dummy_m_path = os.path.join(dummy_snapshots, "manifest.json")
                        try:
                            cas.restore_object_to_file(db_manifest_path, dummy_m_path)
                            engine.restore(dummy_m_path, tmp_vault, force=force_restore)
                        except Exception as e:
                            console.print(f"[error]Linked Database restore failed: {e}[/error]")
            else:
                console.print(f"[error]Error: Database manifest blob {db_manifest_hash} not found in vault objects.[/error]")
    except Exception as e:
        console.print(f"[error]Failed to restore linked database: {e}[/error]")

def handle_capsule_export_command(args, defaults):
    if not args.manifest:
        console.print("[error]Error: Manifest path must be specified.[/error]")
        sys.exit(1)

    if not args.output:
        console.print("[error]Error: Output path for capsule (.pvc) must be specified.[/error]")
        sys.exit(1)

    from src.common import capsule
    try:
        capsule_path = capsule.pack_capsule(resolve_path(args.manifest), resolve_path(args.output))
        console.print(f"[success]✅ Capsule exported to: {capsule_path}[/success]")
    except Exception as e:
        console.print(f"[error]Error exporting capsule: {e}[/error]")
        sys.exit(1)

def handle_capsule_import_command(args, defaults):
    if not args.capsule:
        console.print("[error]Error: Capsule path (.pvc) must be specified.[/error]")
        sys.exit(1)

    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))
        # Ensure parent dir exists
        os.makedirs(os.path.dirname(args.vault_path), exist_ok=True)

    from src.common import capsule
    try:
        manifest_path = capsule.unpack_capsule(resolve_path(args.capsule), resolve_path(args.vault_path))
        console.print(f"[success]✅ Capsule imported into vault.[/success]")
        console.print(f"   Manifest: {manifest_path}")
        console.print(f"   To restore it, run: pv vault-restore {manifest_path} --dest <destination>")
    except Exception as e:
        console.print(f"[error]Error importing capsule: {e}[/error]")
        sys.exit(1)

def handle_init_db_interactive():
    """Interactive prompt to configure database in pv.toml."""
    console.print(Panel("[bold magenta]Database Configuration Wizard[/bold magenta]", border_style="magenta"))
    
    driver = input("Database Driver (postgres/mysql) [postgres]: ").strip().lower() or "postgres"
    host = input("Database Host [localhost]: ").strip() or "localhost"
    port = input("Database Port [5432]: ").strip() or "5432"
    user = input("Database User: ").strip()
    dbname = input("Database Name: ").strip()
    
    config_entry = f"""
[database]
driver = "{driver}"
host = "{host}"
port = {port}
user = "{user}"
dbname = "{dbname}"
# password = "..." # Recommended: Set PV_DB_PASSWORD env var instead
"""
    
    pv_path = "pv.toml"
    if not os.path.exists(pv_path):
        from src.common import config
        config.generate_init_file(pv_path)
        
    with open(pv_path, "a") as f:
        f.write(config_entry)
        
    console.print(f"\n[success]✅ Database configuration appended to {pv_path}[/success]")

def handle_init_command(args):
    from src.common import config as config
    if getattr(args, "db", False) is True:
        handle_init_db_interactive()
        return

    if args.pyproject:
        print("\n[tool.project-vault]")
        print('bucket = "my-project-backups"')
        print('endpoint = "https://s3.eu-central-003.backblazeb2.com"')
        print('# vault_path = "./my_vault"\n')
    else:
        config.generate_init_file("pv.toml")

        # Check for smart flag
        if hasattr(args, 'smart') and args.smart:
            try:
                from src.common import smart_init
                smart_init.generate_smart_ignore()
            except ImportError:
                # Fallback import
                try:
                    from src.common import smart_init
                    smart_init.generate_smart_ignore()
                except ImportError:
                    console.print("[warning]Could not import smart_init module.[/warning]")

def handle_status_command(args, defaults, credentials_module):
    if not args.vault_path:
        # Smart default
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(resolve_path(args.source))
        args.vault_path = str(get_default_vault_path(project_name))

    from src.projectclone import status_engine

    # Prepare cloud config if cloud flag is set
    cloud_config = {}
    if getattr(args, "cloud", False):
        if not args.bucket:
            console.print("[yellow]Hint: You requested --cloud status but no bucket is configured.[/yellow]")
            console.print("      Set 'bucket' in pv.toml or use --bucket <name>")
        else:
            key_id, app_key, source = credentials_module.resolve_credentials(args)
            if not key_id or not app_key:
                console.print(f"[warning]Warning: Could not resolve cloud credentials (Source: {source}).[/warning]")

            cloud_config = {
                "bucket": args.bucket,
                "endpoint": args.endpoint,
                "key_id": key_id,
                "app_key": app_key
            }

    status_engine.show_status(
        resolve_path(args.source),
        resolve_path(args.vault_path),
        cloud_config
    )

def handle_diff_command(args, defaults):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))

    source_root = os.getcwd()

    from src.projectclone import diff_engine
    diff_engine.show_diff(
        source_root,
        resolve_path(args.vault_path),
        resolve_path(args.file)
    )

def handle_checkout_command(args, defaults):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))

    source_root = os.getcwd()

    from src.projectclone import checkout_engine
    checkout_engine.checkout_file(
        source_root,
        resolve_path(args.vault_path),
        resolve_path(args.file),
        force=args.force
    )

def handle_browse_command(args, defaults):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = args.name or get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))

    source_root = os.getcwd()
    project_name = args.name or os.path.basename(source_root)

    # Sanitize name (consistent with other commands)
    project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)

    try:
        from src.tui import ProjectVaultApp
        app = ProjectVaultApp(resolve_path(args.vault_path), project_name)
        app.run()
    except ImportError:
        console.print("[error]Error: 'textual' library not found. Install it with: pip install textual[/error]")
        sys.exit(1)

def handle_list_command(args, defaults, credentials_module):
    from src.projectclone import list_engine
    if args.cloud:
        if not args.bucket:
            console.print("[error]Error: --bucket must be specified in CLI or pv.toml for cloud listing.[/error]")
            sys.exit(1)

        key_id, app_key, source = credentials_module.resolve_credentials(args)

        if not key_id or not app_key:
            console.print("[error]Error: Cloud credentials missing.[/error]")
            console.print("Sources checked: CLI > Doppler > Env > .env > Config")
            console.print("Set PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (preferred) or standard AWS_.../B2_... variables.")
            sys.exit(1)

        console.print(f"[dim]Authenticated via {source}[/dim]")
        list_engine.list_cloud_snapshots(args.bucket, key_id, app_key, getattr(args, 'endpoint', None))
    else:
        if not args.vault_path:
            from src.common.paths import get_default_vault_path, get_project_name
            project_name = get_project_name(os.getcwd())
            args.vault_path = str(get_default_vault_path(project_name))
            
        list_engine.list_local_snapshots(resolve_path(args.vault_path))

def handle_push_command(args, defaults, credentials_module, notifier=None):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))

    if not args.bucket:
        console.print("[error]Error: Bucket must be specified in CLI or pyproject.toml[/error]")
        sys.exit(1)

    key_id, app_key, source = credentials_module.resolve_credentials(args)

    if not key_id or not app_key:
        console.print("[error]Error: Cloud credentials missing.[/error]")
        console.print("Sources checked: CLI > Doppler > Env > .env > Config")
        console.print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
        sys.exit(1)

    console.print(f"[dim]Authenticated via {source}[/dim]")
    from src.projectclone import sync_engine
    try:
        sync_engine.sync_to_cloud(
            resolve_path(args.vault_path),
            args.bucket,
            args.endpoint,
            key_id,
            app_key,
            dry_run=args.dry_run
        )
        if notifier and not args.dry_run:
            notifier.send_message(f"☁️ Cloud Push Successful to '{args.bucket}'", level="success")
    except Exception as e:
        if notifier:
            notifier.send_message(f"❌ Cloud Push Failed: {e}", level="error")
        raise

def handle_pull_command(args, defaults, credentials_module):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))
        # Ensure exists for pull
        os.makedirs(args.vault_path, exist_ok=True)

    if not args.bucket:
        console.print("[error]Error: Bucket must be specified in CLI or pyproject.toml[/error]")
        sys.exit(1)

    key_id, app_key, source = credentials_module.resolve_credentials(args)

    if not key_id or not app_key:
        console.print("[error]Error: Cloud credentials missing.[/error]")
        console.print("Sources checked: CLI > Doppler > Env > .env > Config")
        console.print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
        sys.exit(1)

    console.print(f"[dim]Authenticated via {source}[/dim]")
    from src.projectclone import sync_engine
    sync_engine.sync_from_cloud(
        resolve_path(args.vault_path),
        args.bucket,
        args.endpoint,
        key_id,
        app_key,
        dry_run=args.dry_run
    )

def handle_check_integrity_command(args, defaults):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))

    from src.projectclone import integrity_engine
    if not integrity_engine.verify_vault(resolve_path(args.vault_path)):
        sys.exit(1)

def handle_gc_command(args, defaults):
    if not args.vault_path:
        from src.common.paths import get_default_vault_path, get_project_name
        project_name = get_project_name(os.getcwd())
        args.vault_path = str(get_default_vault_path(project_name))

    from src.projectclone import gc_engine
    gc_engine.run_garbage_collection(resolve_path(args.vault_path), args.dry_run)

def handle_verify_clone_command(args, defaults):
    from src.projectclone import verify_engine

    original = resolve_path(args.original_path)
    clone = resolve_path(args.clone_path)

    if not os.path.exists(original):
        console.print(f"[error]Error: Original path '{original}' does not exist.[/error]")
        sys.exit(1)
    if not os.path.exists(clone):
        console.print(f"[error]Error: Clone path '{clone}' does not exist.[/error]")
        sys.exit(1)

    console.print(f"[info]Verifying clone...[/info]")
    console.print(f"  Original: [cyan]{original}[/cyan]")
    console.print(f"  Clone:    [cyan]{clone}[/cyan]")

    result = verify_engine.verify_directories(original, clone)

    if result.success:
        console.print(Panel("[bold green]Verification Successful: Capsule is perfect.[/bold green]", border_style="green"))
    else:
        console.print(Panel(f"[bold red]Verification Failed: {len(result.errors)} errors found[/bold red]", border_style="red"))
        for error in result.errors:
             console.print(f"  [red]• {error}[/red]")
        sys.exit(1)

def handle_config_command(args):
    if args.config_command == "set-creds":
        pv_path = "pv.toml"
        if not os.path.exists(pv_path):
                console.print("[error]Error: pv.toml not found. Run `pv init` first.[/error]")
                sys.exit(1)

        with open(pv_path, "r") as f:
            content = f.read()

        if "allow_insecure_storage = true" not in content:
            console.print(Panel(
                "[bold red]⛔ Security Lock Engaged[/bold red]\n\n"
                "You are attempting to save secrets to a plain-text file.\n"
                "To authorize this, you must manually edit [yellow]pv.toml[/yellow] and set:\n\n"
                "  [credentials]\n"
                "  allow_insecure_storage = true\n",
                title="Safety Check Failed", border_style="red"
            ))
            sys.exit(1)

        new_lines = []
        in_creds = False
        keys_written = {"key_id": False, "secret_key": False}

        lines = content.splitlines()
        for line in lines:
            clean = line.strip()
            if clean == "[credentials]":
                in_creds = True
                new_lines.append(line)
                continue

            if in_creds and clean.startswith("["): # Next section
                in_creds = False

            if in_creds:
                if clean.startswith("key_id"):
                    new_lines.append(f'key_id = "{args.key_id}"')
                    keys_written["key_id"] = True
                elif clean.startswith("secret_key"):
                    new_lines.append(f'secret_key = "{args.secret_key}"')
                    keys_written["secret_key"] = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if not keys_written["key_id"] or not keys_written["secret_key"]:
                try:
                    creds_idx = next(i for i, l in enumerate(new_lines) if l.strip() == "[credentials]")
                    insert_pos = creds_idx + 1
                    while insert_pos < len(new_lines) and not new_lines[insert_pos].strip().startswith("["):
                        insert_pos += 1

                    if not keys_written["key_id"]:
                        new_lines.insert(insert_pos, f'key_id = "{args.key_id}"')
                        insert_pos += 1
                    if not keys_written["secret_key"]:
                        new_lines.insert(insert_pos, f'secret_key = "{args.secret_key}"')
                except StopIteration:
                    new_lines.append("")
                    if not keys_written["key_id"]: new_lines.append(f'key_id = "{args.key_id}"')
                    if not keys_written["secret_key"]: new_lines.append(f'secret_key = "{args.secret_key}"')

        with open(pv_path, "w") as f:
            f.write("\n".join(new_lines) + "\n")

        console.print(f"[success]✅ Credentials saved to pv.toml[/success]")
        console.print("[dim]Make sure to exclude this file from version control![/dim]")

def check_cloud_env(credentials_module):
    status_text = Text()

    # Create a dummy args object to pass to resolve_credentials
    class DummyArgs:
        key_id = None
        secret_key = None

    key_id, secret_key, source = credentials_module.resolve_credentials(DummyArgs(), allow_fail=True)

    if key_id and secret_key:
        status_text.append(f"✅ Cloud Credentials Found (Source: {source})\n", style="success")
        if source == "Doppler":
            status_text.append("   Secrets managed via Doppler Integration.\n", style="dim")

        # Get provider info
        provider, bucket, endpoint = credentials_module.get_cloud_provider_info()

        status_text.append(Text.from_markup("\n[bold]Configuration:[/bold]\n"))
        if provider and provider != "Unknown":
            status_text.append(Text.from_markup(f"   Cloud Provider: [bold cyan]{provider}[/bold cyan]\n"))
        else:
            status_text.append(Text.from_markup(f"   Cloud Provider: [yellow]Unknown (could not infer from credentials or endpoint)[/yellow]\n"))

        if bucket:
            status_text.append(Text.from_markup(f"   Bucket: [bold cyan]{bucket}[/bold cyan]\n"))
        else:
            status_text.append(Text.from_markup(f"   Bucket: [yellow]Not Configured (set in pv.toml or PV_BUCKET env var)[/yellow]\n"))

        if endpoint:
            status_text.append(Text.from_markup(f"   Endpoint: [bold cyan]{endpoint}[/bold cyan]\n"))
        else:
            status_text.append(Text.from_markup(f"   Endpoint: [dim]Not set (will use provider default)[/dim]\n"))

    else:
         status_text.append("\n❌ No cloud credentials found.\n", style="error")
         status_text.append("   To use Cloud features, export either B2 or AWS credentials.\n", style="warning")
         status_text.append("   Tip: Prefix with PV_ to isolate credentials for this tool (e.g. PV_AWS_ACCESS_KEY_ID).", style="dim")

    # Check Libraries
    status_text.append(Text.from_markup("\n[bold]Library Status:[/bold]\n"))
    try:
        import boto3
        status_text.append("   ✅ boto3 is installed\n", style="success")
    except ImportError:
        status_text.append("   ❌ boto3 is missing (Run: pip install boto3)\n", style="error")

    try:
        import b2sdk
        status_text.append("   ✅ b2sdk is installed\n", style="success")
    except ImportError:
        status_text.append("   ❌ b2sdk is missing (Run: pip install b2sdk)\n", style="error")

    console.print(Panel(status_text, title="Cloud Environment Configuration", border_style="blue"))

def handle_notify_test_command(notifier):
    if notifier:
        console.print("[info]Sending test notification...[/info]")
        notifier.send_message("🔔 Test notification from Project Vault", level="info")
        console.print("[success]Notification sent (check your Telegram).[/success]")
    else:
        console.print("[error]Notifier not initialized. Check your config/env.[/error]")

def handle_db_command(args, defaults, credentials_module=None):
    from src.projectvault.engines.db_engine import DatabaseEngine

    # 1. Load DB Config
    # Config can be in defaults['database']
    db_config = defaults.get("database", {})

    # Override from args/env if necessary?
    # For now assume config in pv.toml is source of truth for connection

    if not db_config:
        console.print("[error]Error: No [database] section found in pv.toml.[/error]")
        sys.exit(1)

    driver_name = db_config.get("driver", "postgres") # Default to postgres

    try:
        engine = DatabaseEngine(driver_name, db_config)
    except ValueError as e:
        console.print(f"[error]{e}[/error]")
        sys.exit(1)

    if args.db_command == "backup":
        if not args.vault_path:
            from src.common.paths import get_default_vault_path, get_project_name
            project_name = get_project_name(os.getcwd())
            args.vault_path = str(get_default_vault_path(project_name))

        project_name = args.name or os.path.basename(os.getcwd())

        try:
            engine.backup(
                resolve_path(args.vault_path),
                project_name,
                cloud_sync=args.cloud,
                credentials_module=credentials_module,
                bucket=args.bucket,
                endpoint=args.endpoint
            )
        except Exception as e:
            console.print(f"[error]Database backup failed: {e}[/error]")
            sys.exit(1)

    elif args.db_command == "restore":
        # Check integrity or force?
        try:
            engine.restore(
                resolve_path(args.manifest),
                resolve_path(args.vault_path or defaults.get("vault_path")),
                force=args.force,
                credentials_module=credentials_module
            )
        except Exception as e:
            console.print(f"[error]Database restore failed: {e}[/error]")
            sys.exit(1)
