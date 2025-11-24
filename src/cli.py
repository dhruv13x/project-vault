#!/usr/bin/env python3
import sys
import os
import argparse
import importlib
import base64
import json
import urllib.request
from rich.console import Console
import pdb # Added for debugging

# Ensure we can import sibling packages
# We are in src/
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add projectclone/src and projectrestore/src to sys.path
sys.path.insert(0, os.path.join(current_dir, "../projectclone/src"))
sys.path.insert(0, os.path.join(current_dir, "../projectrestore/src"))
# Add src/ itself for common
sys.path.insert(0, current_dir)

# Attempt to import common, handling both editable/local and installed package scenarios
try:
    import common.config as config
except ImportError:
    # Fallback: try relative import if running as script/module inside src
    try:
        from .common import config
    except ImportError:
        # Final fallback for some editable installs or specific layouts
        try:
            from src.common import config
        except ImportError:
            # If all fails, assume we are running from installed package context where src is not in path
            # but the package root is.
            import config


def resolve_path(path_str):
    """
    Expands user (~) and environment variables ($VAR) in a path, 
    then returns the absolute path.
    """
    if not path_str:
        return path_str
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path_str)))


def inject_doppler_secrets():
    """
    Checks for DOPPLER_TOKEN and fetches secrets from Doppler API if present.
    Injects them into os.environ.
    """
    token = os.environ.get("DOPPLER_TOKEN")
    if not token:
        return

    console = Console()
    console.print("[bold cyan]🔮 Doppler Token detected. Fetching secrets...[/bold cyan]")

    url = "https://api.doppler.com/v3/configs/config/secrets/download?format=json"
    req = urllib.request.Request(url)

    # Basic Auth: username=token, password=""
    auth_str = f"{token}:"
    b64_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
    req.add_header("Authorization", f"Basic {b64_auth}")

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            secrets = json.load(response)
            
            count = 0
            for key, value in secrets.items():
                # We overwrite existing env vars to allow Doppler to be the source of truth
                # or we can choose to only set if missing.
                # Usually tools prioritize ENV > Config. 
                # Here we treat Doppler as "Better ENV".
                if key not in os.environ:
                    os.environ[key] = str(value)
                    count += 1
            
            console.print(f"[green]✅ Loaded {count} secrets from Doppler.[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to load Doppler secrets: {e}[/red]")


def get_credentials(provider=None):
    """
    Resolves cloud credentials with precedence:
    1. PV_ prefixed variables (PV_AWS_..., PV_B2_...)
    2. Standard variables (AWS_..., B2_...)
    
    Returns:
        (key_id, app_key/secret_key)
    """
    # AWS / S3
    aws_key_pv = os.environ.get("PV_AWS_ACCESS_KEY_ID")
    aws_secret_pv = os.environ.get("PV_AWS_SECRET_ACCESS_KEY")
    
    aws_key_std = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_std = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    # B2
    b2_key_pv = os.environ.get("PV_B2_KEY_ID")
    b2_app_pv = os.environ.get("PV_B2_APP_KEY")
    
    b2_key_std = os.environ.get("B2_KEY_ID")
    b2_app_std = os.environ.get("B2_APP_KEY")
    
    # Resolve
    aws_final_key = aws_key_pv or aws_key_std
    aws_final_secret = aws_secret_pv or aws_secret_std
    
    b2_final_key = b2_key_pv or b2_key_std
    b2_final_app = b2_app_pv or b2_app_std
    
    # If specific provider requested (future use), or just return first valid pair
    # Currently, since S3 and B2 support is somewhat mutually exclusive per command execution (one target),
    # we return the AWS pair if present (as S3 is more generic), otherwise B2.
    
    # However, if the user has BOTH set, we might have ambiguity. 
    # Given the code uses `key_id` and `app_key` generically, we'll prioritize AWS logic if found.
    
    if aws_final_key and aws_final_secret:
        return aws_final_key, aws_final_secret
    
    if b2_final_key and b2_final_app:
        return b2_final_key, b2_final_app
        
    return None, None


def check_cloud_env():
    console = Console()
    console.print("[bold]Checking Cloud Environment Configuration...[/bold]")
    
    # Check B2
    b2_key_pv = os.environ.get("PV_B2_KEY_ID")
    b2_app_pv = os.environ.get("PV_B2_APP_KEY")
    b2_key_std = os.environ.get("B2_KEY_ID")
    b2_app_std = os.environ.get("B2_APP_KEY")
    
    if b2_key_pv and b2_app_pv:
        console.print("[green]✅ Found PV-prefixed B2 Credentials (PV_B2_KEY_ID, PV_B2_APP_KEY)[/green]")
    elif b2_key_std and b2_app_std:
        console.print("[green]✅ Found Standard B2 Credentials (B2_KEY_ID, B2_APP_KEY)[/green]")
    else:
        console.print("[yellow]⚠️  Missing B2 Credentials[/yellow]")

    # Check AWS/S3
    aws_key_pv = os.environ.get("PV_AWS_ACCESS_KEY_ID")
    aws_secret_pv = os.environ.get("PV_AWS_SECRET_ACCESS_KEY")
    aws_key_std = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_std = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    if aws_key_pv and aws_secret_pv:
        console.print("[green]✅ Found PV-prefixed AWS/S3 Credentials (PV_AWS_ACCESS_KEY_ID, PV_AWS_SECRET_ACCESS_KEY)[/green]")
    elif aws_key_std and aws_secret_std:
        console.print("[green]✅ Found Standard AWS/S3 Credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)[/green]")
    else:
        console.print("[yellow]⚠️  Missing AWS/S3 Credentials[/yellow]")

    if not (b2_key_pv or b2_key_std) and not (aws_key_pv or aws_key_std):
        console.print("\n[red]❌ No cloud credentials found.[/red]")
        console.print("   [yellow]To use Cloud features, export either B2 or AWS credentials.[/yellow]")
        console.print("   [dim]Tip: Prefix with PV_ to isolate credentials for this tool (e.g. PV_AWS_ACCESS_KEY_ID).[/dim]")

    try:
        import boto3
        console.print("[green]✅ boto3 is installed[/green]")
    except ImportError:
        console.print("[red]❌ boto3 is missing[/red]")
        console.print("   [yellow]Run:[/yellow] pip install boto3")
    
    try:
        import b2sdk
        console.print("[green]✅ b2sdk is installed[/green]")
    except ImportError:
        console.print("[red]❌ b2sdk is missing[/red]")
        console.print("   [yellow]Run:[/yellow] pip install b2sdk")

def main():
    # 1. Inject Doppler Secrets (Environment Override)
    inject_doppler_secrets()

    # 2. Load File Config
    defaults = config.load_project_config()

    # 3. Merge Environment Config (Doppler/Manual) into Defaults
    # This ensures that if a key exists in Env (from Doppler), it overrides/fills the file config.
    if os.environ.get("PV_BUCKET"):
        defaults["bucket"] = os.environ["PV_BUCKET"]
    if os.environ.get("PV_ENDPOINT"):
        defaults["endpoint"] = os.environ["PV_ENDPOINT"]
    if os.environ.get("PV_VAULT_PATH"):
        defaults["vault_path"] = os.environ["PV_VAULT_PATH"]
    if os.environ.get("PV_RESTORE_PATH"):
        defaults["restore_path"] = os.environ["PV_RESTORE_PATH"]

    # Hijack for pass-through commands to avoid argparse issues with flags like --help
    if len(sys.argv) > 1:
        if sys.argv[1] == "backup":
            try:
                from projectclone import cli as clone_cli
            except ImportError as e:
                print(f"Error executing command 'backup': {e}")
                sys.exit(1)

            # Transform argv from ['pv', 'backup', ...] to ['projectclone', ...]
            sys.argv[0] = "projectclone"
            del sys.argv[1]
            
            # Inject vault_path from config if --dest is missing
            if defaults.get("vault_path") and "--dest" not in sys.argv:
                sys.argv.extend(["--dest", defaults["vault_path"]])
            
            # Inject bucket/endpoint if available in config
            if defaults.get("bucket") and "--bucket" not in sys.argv:
                sys.argv.extend(["--bucket", defaults["bucket"]])
            
            if defaults.get("endpoint") and "--endpoint" not in sys.argv:
                sys.argv.extend(["--endpoint", defaults["endpoint"]])
                
            clone_cli.main()
            sys.exit(0)
            return
        elif sys.argv[1] == "archive-restore":
            try:
                from projectrestore import cli as restore_cli
            except ImportError as e:
                print(f"Error executing command 'archive-restore': {e}")
                sys.exit(1)

            sys.argv[0] = "projectrestore"
            del sys.argv[1]
            restore_cli.main()
            sys.exit(0)
            return

    parser = argparse.ArgumentParser(
        prog="pv",
        description="Project Vault: The Unified Project Lifecycle Manager",
        epilog="Use 'pv <command> --help' for more information on a specific command."
    )
    
    subparsers = parser.add_subparsers(dest="command", title="Available Commands")
    
    # --- Backup Command ---
    backup_parser = subparsers.add_parser("backup", help="Create backups (full, incremental, archive)")
    backup_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectclone")

    # --- Archive Restore Command ---
    archive_restore_parser = subparsers.add_parser("archive-restore", help="Safely restore archive backups")
    archive_restore_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectrestore")

    # --- Vault Command ---
    vault_parser = subparsers.add_parser("vault", help="Content-Addressable Backup to Vault")
    vault_parser.add_argument("source", nargs="?", default=".", help="Source directory")
    vault_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Vault destination path")
    vault_parser.add_argument("--name", help="Project name for organizing snapshots (default: source directory name)")

    # --- Vault Restore Command ---
    vault_restore_parser = subparsers.add_parser("vault-restore", help="Restore from Vault Manifest")
    vault_restore_parser.add_argument("manifest", help="Path to manifest.json")
    vault_restore_parser.add_argument("dest", nargs="?", default=defaults.get("restore_path"), help="Destination directory")

    # --- Push Command ---
    push_parser = subparsers.add_parser("push", help="Push Vault to Cloud Storage (S3/B2)")
    push_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    push_parser.add_argument("--bucket", default=defaults.get("bucket"), help="Target S3/B2 Bucket Name")
    push_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="S3/B2 Endpoint URL")
    push_parser.add_argument("--dry-run", action="store_true", help="Simulate push without uploading")

    # --- Pull Command ---
    pull_parser = subparsers.add_parser("pull", help="Download missing backups from Cloud (S3/B2)")
    pull_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    pull_parser.add_argument("--bucket", default=defaults.get("bucket"), help="Target S3/B2 Bucket Name")
    pull_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="S3/B2 Endpoint URL")
    pull_parser.add_argument("--dry-run", action="store_true", help="Simulate pull without downloading")

    # --- Integrity Check Command ---
    integrity_parser = subparsers.add_parser("check-integrity", help="Verify local vault health")
    integrity_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")

    # --- Garbage Collection Command ---
    gc_parser = subparsers.add_parser("gc", help="Clean up orphaned objects")
    gc_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    gc_parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without removing files")

    # --- Init Command ---
    init_parser = subparsers.add_parser("init", help="Initialize configuration")
    init_parser.add_argument("--pyproject", action="store_true", help="Print configuration for pyproject.toml instead of creating pv.toml")

    # --- Status Command ---
    status_parser = subparsers.add_parser("status", help="Show workspace and vault status")
    status_parser.add_argument("source", nargs="?", default=".", help="Source directory")
    status_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    status_parser.add_argument("--bucket", default=defaults.get("bucket"), help="Target Cloud Bucket")
    status_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="Cloud Endpoint")

    # --- Diff Command ---
    diff_parser = subparsers.add_parser("diff", help="Show changes between workspace and snapshot")
    diff_parser.add_argument("file", help="The file to compare")
    diff_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")

    # --- Checkout Command ---
    checkout_parser = subparsers.add_parser("checkout", help="Restore a specific file from snapshot")
    checkout_parser.add_argument("file", help="The file to restore")
    checkout_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    checkout_parser.add_argument("-f", "--force", action="store_true", help="Overwrite without confirmation")

    # --- List Command ---
    list_parser = subparsers.add_parser("list", help="List available snapshots locally or in the cloud")
    list_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault (optional)")
    list_parser.add_argument("--cloud", action="store_true", help="List backups in Cloud (B2/S3)")
    list_parser.add_argument("--bucket", default=defaults.get("bucket"), help="Target Bucket Name (optional)")
    list_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="S3/B2 Endpoint URL")
    list_parser.add_argument("--limit", type=int, default=10, help="Show only top N backups per project")

    # --- Cloud Env Check Command ---
    subparsers.add_parser("check-env", help="Verify Cloud Environment Variables (S3/B2)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch logic
    try:
        if args.command == "backup":
            from projectclone import cli as clone_cli
            # Hacky: Adjust sys.argv so argparse in the sub-tool sees what it expects
            sys.argv = ["projectclone"] + args.args
            clone_cli.main()
            
        elif args.command == "archive-restore":
            try:
                from projectrestore import cli as restore_cli
            except ImportError as e:
                print(f"Error executing command 'archive-restore': {e}")
                sys.exit(1)
            
            # Inject bucket/endpoint if available in config
            if defaults.get("bucket") and "--bucket" not in args.args:
                args.args.extend(["--bucket", defaults["bucket"]])
            
            if defaults.get("endpoint") and "--endpoint" not in args.args:
                args.args.extend(["--endpoint", defaults["endpoint"]])

            sys.argv = ["projectrestore"] + args.args
            restore_cli.main()
            sys.exit(0)
            return
            
        elif args.command == "vault":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
                return
            
            source_abs = resolve_path(args.source)
            project_name = args.name or os.path.basename(source_abs)
            
            from projectclone import cas_engine
            cas_engine.backup_to_vault(source_abs, resolve_path(args.vault_path), project_name=project_name)

        elif args.command == "vault-restore":
            if not args.dest:
                print("Error: Destination directory must be specified in CLI or 'restore_path' in pv.toml")
                sys.exit(1)
            from projectrestore import restore_engine
            restore_engine.restore_snapshot(resolve_path(args.manifest), resolve_path(args.dest))
            
        elif args.command == "init":
            if args.pyproject:
                print("\n[tool.project-vault]")
                print('bucket = "my-project-backups"')
                print('endpoint = "https://s3.eu-central-003.backblazeb2.com"')
                print('# vault_path = "./my_vault"\n')
            else:
                config.generate_init_file("pv.toml")

        elif args.command == "status":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)

            from projectclone import status_engine
            
            # Prepare cloud config if bucket is present
            cloud_config = {}
            if args.bucket:
                key_id, app_key = get_credentials()
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

        elif args.command == "diff":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
            
            # Heuristic: Assume current directory is source root unless user provides a way to specify it.
            # Ideally, we'd traverse up to find a marker, but for now, CWD is a safe assumption for simple usage.
            source_root = os.getcwd()
            
            from projectclone import diff_engine
            diff_engine.show_diff(
                source_root,
                resolve_path(args.vault_path),
                resolve_path(args.file)
            )

        elif args.command == "checkout":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
            
            source_root = os.getcwd()
            
            from projectclone import checkout_engine
            checkout_engine.checkout_file(
                source_root,
                resolve_path(args.vault_path),
                resolve_path(args.file),
                force=args.force
            )

        elif args.command == "list":
            from projectclone import list_engine
            if args.cloud:
                if not args.bucket:
                    print("Error: --bucket must be specified in CLI or pv.toml for cloud listing.")
                    sys.exit(1)
                
                key_id, app_key = get_credentials()

                if not key_id or not app_key:
                    print("Error: Cloud credentials missing.")
                    print("Set PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (preferred) or standard AWS_.../B2_... variables.")
                    sys.exit(1)
                
                list_engine.list_cloud_snapshots(args.bucket, key_id, app_key, getattr(args, 'endpoint', None))
            else:
                if not args.vault_path:
                    print("Error: vault_path must be specified in CLI or pv.toml for local listing.")
                    sys.exit(1)
                list_engine.list_local_snapshots(resolve_path(args.vault_path))

        elif args.command == "push":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
            if not args.bucket:
                print("Error: Bucket must be specified in CLI or pyproject.toml")
                sys.exit(1)
            
            key_id, app_key = get_credentials()
            
            if not key_id or not app_key:
                print("Error: Cloud credentials missing.")
                print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
                sys.exit(1)
                
            from projectclone import sync_engine
            sync_engine.sync_to_cloud(
                resolve_path(args.vault_path),
                args.bucket,
                args.endpoint,
                key_id,
                app_key,
                dry_run=args.dry_run
            )

        elif args.command == "pull":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
            if not args.bucket:
                print("Error: Bucket must be specified in CLI or pyproject.toml")
                sys.exit(1)

            key_id, app_key = get_credentials()
            
            if not key_id or not app_key:
                print("Error: Cloud credentials missing.")
                print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
                sys.exit(1)
                
            from projectclone import sync_engine
            sync_engine.sync_from_cloud(
                resolve_path(args.vault_path),
                args.bucket,
                args.endpoint,
                key_id,
                app_key,
                dry_run=args.dry_run
            )
            
        elif args.command == "check-integrity":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
            from projectclone import integrity_engine
            if not integrity_engine.verify_vault(resolve_path(args.vault_path)):
                sys.exit(1)
                
        elif args.command == "gc":
            if not args.vault_path:
                print("Error: vault_path must be specified in CLI or pv.toml")
                sys.exit(1)
            from projectclone import gc_engine
            gc_engine.run_garbage_collection(resolve_path(args.vault_path), args.dry_run)

        elif args.command == "check-env":
            check_cloud_env()

    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)

if __name__ == "__main__":
    main()
