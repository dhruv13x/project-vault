#!/usr/bin/env python3
import sys
import os
import argparse
import importlib
from rich.console import Console

# Ensure we can import sibling packages
# We are in src/
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add projectclone/src and projectrestore/src to sys.path
sys.path.insert(0, os.path.join(current_dir, "../projectclone/src"))
sys.path.insert(0, os.path.join(current_dir, "../projectrestore/src"))
sys.path.insert(0, current_dir) # Add src/ itself for common


def b2_check_main():
    console = Console()
    console.print("[bold]Checking B2 Environment Configuration...[/bold]")
    
    key_id = os.environ.get("B2_KEY_ID")
    app_key = os.environ.get("B2_APP_KEY")
    
    if key_id:
        console.print("[green]✅ Found B2_KEY_ID[/green]")
    else:
        console.print("[red]❌ Missing B2_KEY_ID[/red]")
        console.print("   [yellow]Run:[/yellow] export B2_KEY_ID='your_key_id'")

    if app_key:
        console.print("[green]✅ Found B2_APP_KEY[/green]")
    else:
        console.print("[red]❌ Missing B2_APP_KEY[/red]")
        console.print("   [yellow]Run:[/yellow] export B2_APP_KEY='your_app_key'")

    try:
        import boto3
        console.print("[green]✅ boto3 is installed[/green]")
    except ImportError:
        console.print("[red]❌ boto3 is missing[/red]")
        console.print("   [yellow]Run:[/yellow] pip install boto3")

def main():
    parser = argparse.ArgumentParser(
        prog="pv",
        description="Project Vault: The Unified Project Lifecycle Manager",
        epilog="Use 'pv <command> --help' for more information on a specific command."
    )
    
    subparsers = parser.add_subparsers(dest="command", title="Available Commands")
    
    # --- Clone Command ---
    clone_parser = subparsers.add_parser("clone", help="Create backups (full, incremental, archive)")
    clone_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectclone")

    # --- Restore Command ---
    restore_parser = subparsers.add_parser("restore", help="Safely restore backups")
    restore_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectrestore")

    # --- Vault Command ---
    vault_parser = subparsers.add_parser("vault", help="Content-Addressable Backup to Vault")
    vault_parser.add_argument("source", nargs="?", default=".", help="Source directory")
    vault_parser.add_argument("vault_path", help="Vault destination path")

    # --- Vault Restore Command ---
    vault_restore_parser = subparsers.add_parser("vault-restore", help="Restore from Vault Manifest")
    vault_restore_parser.add_argument("manifest", help="Path to manifest.json")
    vault_restore_parser.add_argument("dest", help="Destination directory")

    # --- Sync Command ---
    sync_parser = subparsers.add_parser("sync", help="Sync Vault to Cloud Storage")
    sync_parser.add_argument("vault_path", help="Path to local vault")
    sync_parser.add_argument("--bucket", required=True, help="Target S3/B2 Bucket Name")
    sync_parser.add_argument("--endpoint", required=True, help="S3/B2 Endpoint URL")

    # --- Pull Command ---
    pull_parser = subparsers.add_parser("pull", help="Download missing backups from Cloud")
    pull_parser.add_argument("vault_path", help="Path to local vault")
    pull_parser.add_argument("--bucket", required=True, help="Target S3/B2 Bucket Name")
    pull_parser.add_argument("--endpoint", required=True, help="S3/B2 Endpoint URL")

    # --- Integrity Check Command ---
    integrity_parser = subparsers.add_parser("check-integrity", help="Verify local vault health")
    integrity_parser.add_argument("vault_path", help="Path to local vault")

    # --- B2 Check Command ---
    subparsers.add_parser("b2-check", help="Verify B2 Environment Variables")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch logic
    try:
        if args.command == "clone":
            from projectclone import cli as clone_cli
            # Hacky: Adjust sys.argv so argparse in the sub-tool sees what it expects
            sys.argv = ["projectclone"] + args.args
            clone_cli.main()
            
        elif args.command == "restore":
            from projectrestore import cli as restore_cli
            sys.argv = ["projectrestore"] + args.args
            restore_cli.main()
            
        elif args.command == "vault":
            # Manually invoking the engine logic because the CLI wrapper in projectclone 
            # expects specific arg parsing that we might duplicate or skip.
            # However, reuse the engine directly for cleaner integration here.
            from projectclone import cas_engine
            cas_engine.backup_to_vault(os.path.abspath(args.source), os.path.abspath(args.vault_path))

        elif args.command == "vault-restore":
            from projectrestore import restore_engine
            restore_engine.restore_snapshot(os.path.abspath(args.manifest), os.path.abspath(args.dest))
            
        elif args.command == "sync":
            key_id = os.environ.get("B2_KEY_ID")
            app_key = os.environ.get("B2_APP_KEY")
            
            if not key_id or not app_key:
                print("Error: B2_KEY_ID and B2_APP_KEY environment variables must be set.")
                print("Please export them: export B2_KEY_ID=... B2_APP_KEY=...")
                sys.exit(1)
                
            from projectclone import sync_engine
            sync_engine.sync_to_cloud(
                os.path.abspath(args.vault_path),
                args.bucket,
                args.endpoint,
                key_id,
                app_key
            )

        elif args.command == "pull":
            key_id = os.environ.get("B2_KEY_ID")
            app_key = os.environ.get("B2_APP_KEY")
            
            if not key_id or not app_key:
                print("Error: B2_KEY_ID and B2_APP_KEY environment variables must be set.")
                print("Please export them: export B2_KEY_ID=... B2_APP_KEY=...")
                sys.exit(1)
                
            from projectclone import sync_engine
            sync_engine.sync_from_cloud(
                os.path.abspath(args.vault_path),
                args.bucket,
                args.endpoint,
                key_id,
                app_key
            )
            
        elif args.command == "check-integrity":
            from projectclone import integrity_engine
            if not integrity_engine.verify_vault(os.path.abspath(args.vault_path)):
                sys.exit(1)

        elif args.command == "b2-check":
            b2_check_main()

    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)

if __name__ == "__main__":
    main()
