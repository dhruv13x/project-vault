#!/usr/bin/env python3
# src/cli.py

import sys
import os
import argparse
import importlib
import base64
import json
import urllib.request

# Import console
from src.common.console import console

# Import help functions and actions from new module
from src.cli_help import (
    print_main_help,
    RichHelpAction,
    RichVaultHelpAction,
    RichVaultRestoreHelpAction,
    RichPushHelpAction,
    RichPullHelpAction,
    RichListHelpAction,
    RichVerifyCloneHelpAction,
    RichDbHelpAction
)

# Import command handlers from new dispatch module
from src.cli_dispatch import (
    handle_vault_command,
    handle_vault_restore_command,
    handle_verify_clone_command,
    handle_init_command,
    handle_status_command,
    handle_diff_command,
    handle_checkout_command,
    handle_browse_command,
    handle_list_command,
    handle_push_command,
    handle_pull_command,
    handle_check_integrity_command,
    handle_gc_command,
    handle_config_command,
    handle_notify_test_command,
    check_cloud_env,
    handle_capsule_export_command,
    handle_capsule_import_command,
    handle_db_command
)

# Try to import RichHelpFormatter for better help output
try:
    from rich_argparse import RichHelpFormatter
except ImportError:
    RichHelpFormatter = argparse.HelpFormatter

# Attempt to import common, handling both editable/local and installed package scenarios
try:
    from src.common import config
    from src.common import credentials
    from src.common.banner import print_logo
except ImportError:
    # Fallback: try relative import if running as script/module inside src
    try:
        from .common import config
        from .common import credentials
        from .common.banner import print_logo
    except ImportError:
        # Final fallback
        import common.config as config
        import common.credentials as credentials
        from common.banner import print_logo


def resolve_path(path_str):
    """
    Expands user (~) and environment variables ($VAR) in a path, 
    then returns the absolute path.
    """
    if not path_str:
        return path_str
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path_str)))


# check_cloud_env moved to src/cli_dispatch.py


# Define more print_..._help() functions for other commands here...

# --- Custom Argparse Actions ---

# Moved to src/cli_help.py

# Define more Rich...HelpAction classes for other commands here...


def main():
    try:
        _real_main()
    except Exception as e:
        console.print(f"[error]Error: {e}[/error]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[warning]Interrupted.[/warning]")
        sys.exit(130)

def _real_main():
    print_logo()
    
    # 1. Load File Config (Lowest Priority)
    defaults = config.load_project_config()
    
    # 2. Get Merged Environment (Doppler > Real Env > .env)
    full_env = credentials.get_full_env()

    # 3. Merge Environment into Defaults (Env > Config)
    # Map Env Vars to Config Keys
    env_mapping = {
        "PV_BUCKET": "bucket",
        "PV_ENDPOINT": "endpoint",
        "PV_VAULT_PATH": "vault_path",
        "PV_RESTORE_PATH": "restore_path"
    }
    
    for env_var, config_key in env_mapping.items():
        if full_env.get(env_var):
            defaults[config_key] = full_env[env_var]

    # Initialize Notifier
    try:
        from common.notifications import TelegramNotifier
        notifier = TelegramNotifier(defaults)
    except ImportError:
        # Fallback if running in different context
        try:
            from common.notifications import TelegramNotifier
            notifier = TelegramNotifier(defaults)
        except ImportError:
            notifier = None

    # Hijack for pass-through commands to avoid argparse issues with flags like --help
    # Note: 'clone' and 'restore' are the new preferred names for the sub-tools.
    if len(sys.argv) > 1 and sys.argv[1] in ["backup", "archive-restore"]:
        subcommand = sys.argv[1]
        try:
            module_name = "projectclone" if subcommand == "backup" else "projectrestore"
            cli_module = importlib.import_module(f"src.{module_name}.cli")
        except ImportError as e:
            console.print(f"[error]Error executing command '{subcommand}': {e}[/error]")
            sys.exit(1)

        # Reconstruct argv for the sub-tool
        sys.argv[0] = module_name
        del sys.argv[1]

        # Use imported paths for smart defaults
        try:
            from src.common.paths import get_default_backup_path, get_project_name, get_default_restore_destination
        except ImportError:
            # Fallback if common paths not available in src context (e.g. installed package)
            from common.paths import get_default_backup_path, get_project_name, get_default_restore_destination
        
        project_name = get_project_name(os.getcwd())

        if subcommand == "backup":
            # Inject --dest for backup command
            if "--dest" not in sys.argv:
                if defaults.get("vault_path"): # Check if user configured vault_path
                    sys.argv.extend(["--dest", defaults["vault_path"]])
                else:
                    is_archive = "--archive" in sys.argv or "-a" in sys.argv
                    backup_type = "archive" if is_archive else "folder"
                    default_path = get_default_backup_path(project_name, backup_type=backup_type)
                    sys.argv.extend(["--dest", str(default_path)])
        elif subcommand == "archive-restore":
            # Inject --extract-dir for archive-restore command
            if "--extract-dir" not in sys.argv:
                if defaults.get("restore_path"):
                    sys.argv.extend(["--extract-dir", defaults["restore_path"]])
                else:
                    default_path = get_default_restore_destination(project_name)
                    sys.argv.extend(["--extract-dir", str(default_path)])
            
            # Inject --backup-dir for archive-restore command (where to look for archives)
            if "--backup-dir" not in sys.argv:
                if defaults.get("vault_path"): # Using vault_path as a general storage root
                    sys.argv.extend(["--backup-dir", defaults["vault_path"]])
                else:
                    # Default to where archive backups are usually stored
                    default_path = get_default_backup_path(project_name, backup_type="archive")
                    sys.argv.extend(["--backup-dir", str(default_path)])


        if defaults.get("bucket") and "--bucket" not in sys.argv:
            sys.argv.extend(["--bucket", defaults["bucket"]])
        if defaults.get("endpoint") and "--endpoint" not in sys.argv:
            sys.argv.extend(["--endpoint", defaults["endpoint"]])
            
        cli_module.main()
        return


    parser = argparse.ArgumentParser(
        prog="pv",
        description="Project Vault: The Unified Project Lifecycle Manager",
        add_help=False # We are using our own help action
    )
    parser.add_argument(
        '-h', '--help', 
        action=RichHelpAction, 
        help='Show this help message and exit.'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 8.0.0', 
        help="Show program's version number and exit."
    )
    
    subparsers = parser.add_subparsers(dest="command", title="Available Commands")
    
    # Define subparsers with RichHelpFormatter for their own help messages
    backup_parser = subparsers.add_parser("backup", help="Create backups (legacy file-based). Pass -h for more.", add_help=False)
    backup_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectclone")

    archive_restore_parser = subparsers.add_parser("archive-restore", help="Safely restore legacy archive backups. Pass -h for more.", add_help=False)
    archive_restore_parser.add_argument("--include-db", action="store_true", help="Automatically restore bundled database if found")
    archive_restore_parser.add_argument("--force", action="store_true", help="Force database schema recreation")
    archive_restore_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectrestore")
    
    # --- Vault Command ---
    vault_parser = subparsers.add_parser("vault", add_help=False)
    vault_parser.add_argument("-h", "--help", action=RichVaultHelpAction)
    vault_parser.add_argument("source", nargs="?", default=".")
    vault_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    vault_parser.add_argument("--name", help="Project name for organizing snapshots (default: source directory name)")
    vault_parser.add_argument("--symlinks", action="store_true", help="preserve symlinks instead of copying targets")
    vault_parser.add_argument("--cloud", action="store_true", help="push to cloud after creating snapshot")
    vault_parser.add_argument("--bucket", default=defaults.get("bucket"), help="target cloud bucket")
    vault_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="cloud endpoint")
    vault_parser.add_argument("--include-db", action="store_true", help="include database snapshot")

    # --- Vault Restore Command ---
    vault_restore_parser = subparsers.add_parser("vault-restore", add_help=False)
    vault_restore_parser.add_argument("-h", "--help", action=RichVaultRestoreHelpAction)
    vault_restore_parser.add_argument("manifest", help="Path to manifest.json")
    vault_restore_parser.add_argument("dest", nargs="?", default=defaults.get("restore_path"))
    vault_restore_parser.add_argument("--force", action="store_true", help="Drop and recreate database schema during restore")

    # --- Verify Clone Command ---
    verify_clone_parser = subparsers.add_parser("verify-clone", add_help=False)
    verify_clone_parser.add_argument("-h", "--help", action=RichVerifyCloneHelpAction)
    verify_clone_parser.add_argument("original_path", help="Original source directory")
    verify_clone_parser.add_argument("clone_path", help="Restored directory to verify")

    # --- Capsule Command (Alias Wrapper) ---
    capsule_parser = subparsers.add_parser("capsule", help="Manage project capsules (snapshots)", formatter_class=RichHelpFormatter)
    capsule_subparsers = capsule_parser.add_subparsers(dest="capsule_command", title="Capsule Actions")

    # pv capsule create -> pv vault
    capsule_create_parser = capsule_subparsers.add_parser("create", add_help=False)
    capsule_create_parser.add_argument("-h", "--help", action=RichVaultHelpAction)
    capsule_create_parser.add_argument("source", nargs="?", default=".")
    capsule_create_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    capsule_create_parser.add_argument("--name", help="Project name")
    capsule_create_parser.add_argument("--symlinks", action="store_true", help="preserve symlinks instead of copying targets")
    capsule_create_parser.add_argument("--cloud", action="store_true", help="push to cloud after creating snapshot")
    capsule_create_parser.add_argument("--bucket", default=defaults.get("bucket"))
    capsule_create_parser.add_argument("--endpoint", default=defaults.get("endpoint"))
    capsule_create_parser.add_argument("--include-db", action="store_true", help="include database snapshot")

    # pv capsule restore -> pv vault-restore
    capsule_restore_parser = capsule_subparsers.add_parser("restore", add_help=False)
    capsule_restore_parser.add_argument("-h", "--help", action=RichVaultRestoreHelpAction)
    capsule_restore_parser.add_argument("manifest", help="Path to manifest.json")
    capsule_restore_parser.add_argument("dest", nargs="?", default=defaults.get("restore_path"))

    # pv capsule export
    capsule_export_parser = capsule_subparsers.add_parser("export", help="Export a snapshot to a .pvc capsule file")
    capsule_export_parser.add_argument("manifest", help="Path to manifest.json to export")
    capsule_export_parser.add_argument("-o", "--output", required=True, help="Output .pvc file path")

    # pv capsule import
    capsule_import_parser = capsule_subparsers.add_parser("import", help="Import a .pvc capsule file into the vault")
    capsule_import_parser.add_argument("capsule", help="Path to .pvc capsule file")
    capsule_import_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Target vault path")

    # --- Database Command ---
    db_parser = subparsers.add_parser("db", add_help=False)
    db_parser.add_argument("-h", "--help", action=RichDbHelpAction)
    db_subparsers = db_parser.add_subparsers(dest="db_command", title="Database Actions")

    # pv db backup
    db_backup_parser = db_subparsers.add_parser("backup", help="Backup database to vault")
    db_backup_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    db_backup_parser.add_argument("--name", help="Project/Database name")
    db_backup_parser.add_argument("--cloud", action="store_true", help="Push to cloud immediately")
    db_backup_parser.add_argument("--bucket", default=defaults.get("bucket"))
    db_backup_parser.add_argument("--endpoint", default=defaults.get("endpoint"))

    # pv db restore
    db_restore_parser = db_subparsers.add_parser("restore", help="Restore database from snapshot")
    db_restore_parser.add_argument("manifest", help="Path to manifest.json")
    db_restore_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    db_restore_parser.add_argument("--force", action="store_true", help="Drop and recreate database schema")

    # --- Push Command ---
    push_parser = subparsers.add_parser("push", add_help=False)
    push_parser.add_argument("-h", "--help", action=RichPushHelpAction)
    push_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    push_parser.add_argument("--bucket", default=defaults.get("bucket"))
    push_parser.add_argument("--endpoint", default=defaults.get("endpoint"))
    push_parser.add_argument("--dry-run", action="store_true")

    # --- Pull Command ---
    pull_parser = subparsers.add_parser("pull", add_help=False)
    pull_parser.add_argument("-h", "--help", action=RichPullHelpAction)
    pull_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    pull_parser.add_argument("--bucket", default=defaults.get("bucket"))
    pull_parser.add_argument("--endpoint", default=defaults.get("endpoint"))
    pull_parser.add_argument("--dry-run", action="store_true")

    # --- Integrity Check Command ---
    integrity_parser = subparsers.add_parser("check-integrity", help="Verify local vault health", formatter_class=RichHelpFormatter)
    integrity_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")

    # --- Garbage Collection Command ---
    gc_parser = subparsers.add_parser("gc", help="Clean up orphaned objects", formatter_class=RichHelpFormatter)
    gc_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    gc_parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without removing files")

    # --- Init Command ---
    init_parser = subparsers.add_parser("init", help="Initialize configuration", formatter_class=RichHelpFormatter)
    init_parser.add_argument("--pyproject", action="store_true", help="Print configuration for pyproject.toml instead of creating pv.toml")
    init_parser.add_argument("--smart", action="store_true", help="Auto-detect project type and generate .pvignore")
    init_parser.add_argument("--db", action="store_true", help="Interactive database configuration")

    # --- Status Command ---
    status_parser = subparsers.add_parser("status", help="Show workspace and vault status", formatter_class=RichHelpFormatter)
    status_parser.add_argument("source", nargs="?", default=".", help="Source directory")
    status_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    status_parser.add_argument("--bucket", default=defaults.get("bucket"), help="Target Cloud Bucket")
    status_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="Cloud Endpoint")
    status_parser.add_argument("--cloud", action="store_true", help="Check cloud synchronization status")

    # --- Diff Command ---
    diff_parser = subparsers.add_parser("diff", help="Show changes between workspace and snapshot", formatter_class=RichHelpFormatter)
    diff_parser.add_argument("file", help="The file to compare")
    diff_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")

    # --- Checkout Command ---
    checkout_parser = subparsers.add_parser("checkout", help="Restore a specific file from snapshot", formatter_class=RichHelpFormatter)
    checkout_parser.add_argument("file", help="The file to restore")
    checkout_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    checkout_parser.add_argument("-f", "--force", action="store_true", help="Overwrite without confirmation")

    # --- Browse Command ---
    browse_parser = subparsers.add_parser("browse", help="Interactive Time Machine TUI", formatter_class=RichHelpFormatter)
    browse_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    browse_parser.add_argument("--name", help="Project name (default: current directory name)")

    # --- List Command ---
    list_parser = subparsers.add_parser("list", add_help=False)
    list_parser.add_argument("-h", "--help", action=RichListHelpAction)
    list_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    list_parser.add_argument("--cloud", action="store_true")
    list_parser.add_argument("--bucket", default=defaults.get("bucket"))
    list_parser.add_argument("--endpoint", default=defaults.get("endpoint"))
    list_parser.add_argument("--limit", type=int, default=10)

    # --- Config Command Group ---
    config_parser = subparsers.add_parser("config", help="Manage configuration", formatter_class=RichHelpFormatter)
    config_subparsers = config_parser.add_subparsers(dest="config_command", title="Config Actions")
    
    # set-creds
    set_creds_parser = config_subparsers.add_parser("set-creds", help="Save credentials to pv.toml (Insecure Storage)", formatter_class=RichHelpFormatter)
    set_creds_parser.add_argument("--key-id", required=True, help="Cloud Access Key ID")
    set_creds_parser.add_argument("--secret-key", required=True, help="Cloud Secret Key")

    # --- Cloud Env Check Command ---
    subparsers.add_parser("check-env", help="Verify Cloud Environment Variables (S3/B2)", formatter_class=RichHelpFormatter)

    # --- Notify Test Command ---
    subparsers.add_parser("notify-test", help="Send a test notification", formatter_class=RichHelpFormatter)


    # Simplified entry point: if no command is given, show our rich help.
    if len(sys.argv) == 1:
        print_main_help()
        sys.exit(0)

    args, unknown = parser.parse_known_args()

    if not hasattr(args, 'command') or not args.command:
        # This handles cases where only flags like -v are passed
        # without a command. We show help and exit.
        print_main_help()
        sys.exit(0)

    # Dispatch logic
    # The clone/restore commands are handled by the special block at the top.
    # This section handles the direct commands.
    if args.command == "vault":
        handle_vault_command(args, defaults, notifier, credentials)

    elif args.command == "vault-restore":
        handle_vault_restore_command(args, defaults)

    elif args.command == "verify-clone":
        handle_verify_clone_command(args, defaults)

    elif args.command == "capsule":
        if args.capsule_command == "create":
            # Map to vault command handler
            handle_vault_command(args, defaults, notifier, credentials)
        elif args.capsule_command == "restore":
            # Map to vault-restore command handler
            handle_vault_restore_command(args, defaults)
        elif args.capsule_command == "export":
            handle_capsule_export_command(args, defaults)
        elif args.capsule_command == "import":
            handle_capsule_import_command(args, defaults)
        else:
             from src.cli_help import print_capsule_help
             print_capsule_help()

    elif args.command == "init":
        handle_init_command(args)

    elif args.command == "status":
        handle_status_command(args, defaults, credentials)

    elif args.command == "diff":
        handle_diff_command(args, defaults)

    elif args.command == "checkout":
        handle_checkout_command(args, defaults)

    elif args.command == "browse":
        handle_browse_command(args, defaults)

    elif args.command == "list":
        handle_list_command(args, defaults, credentials)

    elif args.command == "push":
        handle_push_command(args, defaults, credentials, notifier)

    elif args.command == "pull":
        handle_pull_command(args, defaults, credentials)

    elif args.command == "check-integrity":
        handle_check_integrity_command(args, defaults)

    elif args.command == "gc":
        handle_gc_command(args, defaults)

    elif args.command == "config":
        handle_config_command(args)

    elif args.command == "check-env":
        check_cloud_env(credentials)

    elif args.command == "notify-test":
        handle_notify_test_command(notifier)

    elif args.command == "db":
        handle_db_command(args, defaults, credentials)

if __name__ == "__main__":
    main()