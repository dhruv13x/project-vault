#!/usr/bin/env python3
# src/cli.py

import sys
import os
import argparse
import importlib
import base64
import json
import urllib.request
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Try to import RichHelpFormatter for better help output
try:
    from rich_argparse import RichHelpFormatter
except ImportError:
    RichHelpFormatter = argparse.HelpFormatter

# Define custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "command": "bold magenta",
})
console = Console(theme=custom_theme)

# Ensure we can import sibling packages
# We are in src/
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add projectclone/src and projectrestore/src to sys.path
sys.path.insert(0, os.path.join(current_dir, "../projectclone/src"))
sys.path.insert(0, os.path.join(current_dir, "../projectrestore/src"))
# Add project-vault-core/src to sys.path
sys.path.insert(0, os.path.join(current_dir, "../project-vault-core/src"))
# Add src/ itself for backward compatibility (though strictly we shouldn't need it for core anymore)
sys.path.insert(0, current_dir)

# Attempt to import common, handling both editable/local and installed package scenarios
try:
    import common.config as config
    import common.credentials as credentials
    from common.banner import print_logo
except ImportError:
    # Fallback: try relative import if running as script/module inside src
    try:
        from .common import config
        from .common import credentials
        from .common.banner import print_logo
    except ImportError:
        # Final fallback for some editable installs or specific layouts
        try:
            from src.common import config
            from src.common import credentials
            from src.common.banner import print_logo
        except ImportError:
            # If all fails, assume we are running from installed package context where src is not in path
            # but the package root is.
            import config
            import credentials
            from common.banner import print_logo


def resolve_path(path_str):
    """
    Expands user (~) and environment variables ($VAR) in a path, 
    then returns the absolute path.
    """
    if not path_str:
        return path_str
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path_str)))


def check_cloud_env():
    status_text = Text()
    
    # Create a dummy args object to pass to resolve_credentials
    class DummyArgs:
        key_id = None
        secret_key = None
        
    key_id, secret_key, source = credentials.resolve_credentials(DummyArgs(), allow_fail=True)
    
    if key_id and secret_key:
        status_text.append(f"✅ Cloud Credentials Found (Source: {source})\n", style="success")
        if source == "Doppler":
            status_text.append("   Secrets managed via Doppler Integration.\n", style="dim")
    else:
         status_text.append("\n❌ No cloud credentials found.\n", style="error")
         status_text.append("   To use Cloud features, export either B2 or AWS credentials.\n", style="warning")
         status_text.append("   Tip: Prefix with PV_ to isolate credentials for this tool (e.g. PV_AWS_ACCESS_KEY_ID).", style="dim")

    # Check Libraries
    status_text.append("\nLibrary Status:\n", style="bold underline")
    try:
        import boto3
        status_text.append("✅ boto3 is installed\n", style="success")
    except ImportError:
        status_text.append("❌ boto3 is missing (Run: pip install boto3)\n", style="error")
    
    try:
        import b2sdk
        status_text.append("✅ b2sdk is installed\n", style="success")
    except ImportError:
        status_text.append("❌ b2sdk is missing (Run: pip install b2sdk)\n", style="error")

    console.print(Panel(status_text, title="Cloud Environment Configuration", border_style="blue"))


# --- Help Panel Functions ---

def print_vault_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv vault[/] [yellow][source] [vault_path][/] [magenta][--name <name>]

Creates a content-addressable snapshot of the [yellow]source[/] directory (default: current dir) into the [yellow]vault_path[/].

[bold]Arguments:[/bold]
  [yellow]source[/]          Source directory to back up. Defaults to '.'.
  [yellow]vault_path[/]      Destination vault directory. Can be set in config.
  [yellow]--name <name>[/]    Set a custom project name for the snapshot.
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv vault`[/]", border_style="blue"))

def print_vault_restore_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv vault-restore[/] [yellow]<manifest> <dest>

Restores a project from a snapshot's [yellow]manifest.json[/] file to the [yellow]dest[/] directory.

[bold]Arguments:[/bold]
  [yellow]manifest[/]        Path to the `manifest.json` file of the snapshot to restore.
  [yellow]dest[/]            Directory to restore the project into.
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv vault-restore`[/]", border_style="blue"))

def print_push_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv push[/] [yellow][vault_path][/] [magenta][--bucket <B>] [--endpoint <E>] [--dry-run][/]

Pushes the contents of the local vault to cloud storage (S3/B2).

[bold]Arguments:[/bold]
  [yellow]vault_path[/]      Path to the local vault. Can be set in config.
  [yellow]--bucket <B>[/]     Target cloud bucket name. Required.
  [yellow]--endpoint <E>[/]   (Optional) Cloud endpoint URL for S3-compatible services.
  [yellow]--dry-run[/]         Simulate the push without uploading files.
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv push`[/]", border_style="blue"))

def print_pull_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv pull[/] [yellow][vault_path][/] [magenta][--bucket <B>] [--endpoint <E>] [--dry-run][/]

Pulls missing objects from cloud storage into the local vault.

[bold]Arguments:[/bold]
  [yellow]vault_path[/]      Path to the local vault. Can be set in config.
  [yellow]--bucket <B>[/]     Target cloud bucket name. Required.
  [yellow]--endpoint <E>[/]   (Optional) Cloud endpoint URL for S3-compatible services.
  [yellow]--dry-run[/]         Simulate the pull without downloading files.
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv pull`[/]", border_style="blue"))

def print_list_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv list[/] [yellow][vault_path][/] [magenta][--cloud] [--bucket <B>] ...[/]

Lists available snapshots, either locally or in the cloud.

[bold]Arguments:[/bold]
  [yellow]vault_path[/]      Path to the local vault for local listings.
  [yellow]--cloud[/]         List snapshots from the cloud instead of locally.
  [yellow]--bucket <B>[/]     Cloud bucket to list from (required for --cloud).
  [yellow]--limit <N>[/]      Show only the top N snapshots. Default: 10.
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv list`[/]", border_style="blue"))

# Define more print_..._help() functions for other commands here...

# --- Custom Argparse Actions ---

class RichVaultHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_vault_help(); p.exit()

class RichVaultRestoreHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_vault_restore_help(); p.exit()

class RichPushHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_push_help(); p.exit()

class RichPullHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_pull_help(); p.exit()

class RichListHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_list_help(); p.exit()

# Define more Rich...HelpAction classes for other commands here...


def print_main_help():
    """Prints the main help panel using rich."""
    grid = Text.from_markup(
        """
[bold green]Usage:[/] [cyan]pv[/] [yellow]<command>[/] [magenta][<args>...][/]

[bold green]Core Commands[/bold green]
  [cyan]backup[/cyan]          Create a new backup of a project (legacy file-based).
  [cyan]archive-restore[/cyan] Restore a project from a legacy file-based backup.
  [cyan]vault[/cyan]          Create a new content-addressable snapshot of a project.
  [cyan]vault-restore[/cyan]  Restore a project from a vault snapshot.

[bold green]Cloud Commands[/bold green]
  [cyan]push[/cyan]           Push vault contents to cloud storage (S3/B2).
  [cyan]pull[/cyan]           Pull vault contents from cloud storage.
  [cyan]list --cloud[/cyan]   List snapshots available in the cloud.

[bold green]Local & Maintenance Commands[/bold green]
  [cyan]status[/cyan]         Show workspace and vault status vs last snapshot.
  [cyan]list[/cyan]           List local snapshots.
  [cyan]diff[/cyan]           Show changes between workspace and a file in the snapshot.
  [cyan]checkout[/cyan]      Restore a specific file from the last snapshot.
  [cyan]gc[/cyan]             Clean up orphaned objects from the vault.
  [cyan]check-integrity[/cyan] Verify the integrity of the local vault.
  [cyan]init[/cyan]            Create a default `pv.toml` configuration file.
  [cyan]check-env[/cyan]      Verify cloud environment variables are set.

[bold green]Global Options[/bold green]
  [yellow]-h, --help[/yellow]      Show this help message and exit.
  [yellow]-v, --version[/yellow]   Show program's version number and exit.
"""
    )
    panel = Panel(
        grid,
        title="[bold magenta]Project Vault[/bold magenta] - The Unified Project Lifecycle Manager",
        subtitle="[default]Run '[cyan]pv <command> --help[/cyan]' for details on a command's flags.",
        border_style="blue",
    )
    console.print(panel)


class RichHelpAction(argparse.Action):
    """
A custom argparse action to show a rich-formatted help panel and exit.
    """
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print_main_help()
        parser.exit()


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
            cli_module = importlib.import_module(f"{module_name}.cli")
        except ImportError as e:
            console.print(f"[error]Error executing command '{subcommand}': {e}[/error]")
            sys.exit(1)

        # Reconstruct argv for the sub-tool
        sys.argv[0] = module_name
        del sys.argv[1]

        # Inject config values if not present in args
        if defaults.get("vault_path") and "--dest" not in sys.argv:
            sys.argv.extend(["--dest", defaults["vault_path"]])
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
        version='%(prog)s 2.0.0', # Placeholder version
        help="Show program's version number and exit."
    )
    
    subparsers = parser.add_subparsers(dest="command", title="Available Commands")
    
    # Define subparsers with RichHelpFormatter for their own help messages
    backup_parser = subparsers.add_parser("backup", help="Create backups (legacy file-based). Pass -h for more.", add_help=False)
    backup_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectclone")

    archive_restore_parser = subparsers.add_parser("archive-restore", help="Safely restore legacy archive backups. Pass -h for more.", add_help=False)
    archive_restore_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for projectrestore")
    
    # --- Vault Command ---
    vault_parser = subparsers.add_parser("vault", add_help=False)
    vault_parser.add_argument("-h", "--help", action=RichVaultHelpAction)
    vault_parser.add_argument("source", nargs="?", default=".")
    vault_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"))
    vault_parser.add_argument("--name", help="Project name for organizing snapshots (default: source directory name)")

    # --- Vault Restore Command ---
    vault_restore_parser = subparsers.add_parser("vault-restore", add_help=False)
    vault_restore_parser.add_argument("-h", "--help", action=RichVaultRestoreHelpAction)
    vault_restore_parser.add_argument("manifest", help="Path to manifest.json")
    vault_restore_parser.add_argument("dest", nargs="?", default=defaults.get("restore_path"))

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

    # --- Status Command ---
    status_parser = subparsers.add_parser("status", help="Show workspace and vault status", formatter_class=RichHelpFormatter)
    status_parser.add_argument("source", nargs="?", default=".", help="Source directory")
    status_parser.add_argument("vault_path", nargs="?", default=defaults.get("vault_path"), help="Path to local vault")
    status_parser.add_argument("--bucket", default=defaults.get("bucket"), help="Target Cloud Bucket")
    status_parser.add_argument("--endpoint", default=defaults.get("endpoint"), help="Cloud Endpoint")

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
        if not args.vault_path:
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)

        source_abs = resolve_path(args.source)
        project_name = args.name or os.path.basename(source_abs)

        # Extract hooks
        hooks = defaults.get("hooks", {})
        if hooks:
            console.print("[bold yellow]⚠ Lifecycle Hooks Detected[/bold yellow]")
            console.print("   Executing arbitrary shell commands defined in pv.toml.")

        from projectclone import cas_engine
        try:
            manifest_path = cas_engine.backup_to_vault(
                source_abs, 
                resolve_path(args.vault_path), 
                project_name=project_name,
                hooks=hooks
            )
            if notifier:
                notifier.send_message(f"✅ Snapshot created for '{project_name}'\nManifest: {manifest_path}", level="success")
        except Exception as e:
            if notifier:
                notifier.send_message(f"🚨 Vault Snapshot Failed: {e}", level="error")
            raise

    elif args.command == "vault-restore":
        if not args.dest:
            console.print("[error]Error: Destination directory must be specified in CLI or 'restore_path' in pv.toml[/error]")
            sys.exit(1)

        # Extract hooks
        hooks = defaults.get("hooks", {})
        if hooks:
            console.print("[bold red]⚠ Lifecycle Hooks Detected[/bold red]")
            console.print("   This will execute shell commands defined in the snapshot configuration.")
            console.print("   Ensure you trust the source of this backup.")

        from projectrestore import restore_engine
        restore_engine.restore_snapshot(
            resolve_path(args.manifest), 
            resolve_path(args.dest),
            hooks=hooks
        )

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
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)

        from projectclone import status_engine

        # Prepare cloud config if bucket is present
        cloud_config = {}
        if args.bucket:
            key_id, app_key, source = credentials.resolve_credentials(args)
            if key_id and app_key:
                # Quietly add source info, status engine might use it or we can log it
                pass
                
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
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)

        source_root = os.getcwd()

        from projectclone import diff_engine
        diff_engine.show_diff(
            source_root,
            resolve_path(args.vault_path),
            resolve_path(args.file)
        )

    elif args.command == "checkout":
        if not args.vault_path:
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)

        source_root = os.getcwd()

        from projectclone import checkout_engine
        checkout_engine.checkout_file(
            source_root,
            resolve_path(args.vault_path),
            resolve_path(args.file),
            force=args.force
        )

    elif args.command == "browse":
        if not args.vault_path:
            console.print("[error]Error: vault_path must be specified.[/error]")
            sys.exit(1)
            
        source_root = os.getcwd()
        project_name = args.name or os.path.basename(source_root)
        
        # Sanitize name (consistent with other commands)
        import re
        project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
        
        try:
            from src.tui import ProjectVaultApp
            app = ProjectVaultApp(resolve_path(args.vault_path), project_name)
            app.run()
        except ImportError:
            console.print("[error]Error: 'textual' library not found. Install it with: pip install textual[/error]")
            sys.exit(1)

    elif args.command == "list":
        from projectclone import list_engine
        if args.cloud:
            if not args.bucket:
                console.print("[error]Error: --bucket must be specified in CLI or pv.toml for cloud listing.[/error]")
                sys.exit(1)
            
            key_id, app_key, source = credentials.resolve_credentials(args)

            if not key_id or not app_key:
                console.print("[error]Error: Cloud credentials missing.[/error]")
                console.print("Sources checked: CLI > Doppler > Env > .env > Config")
                console.print("Set PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (preferred) or standard AWS_.../B2_... variables.")
                sys.exit(1)
            
            console.print(f"[dim]Authenticated via {source}[/dim]")
            list_engine.list_cloud_snapshots(args.bucket, key_id, app_key, getattr(args, 'endpoint', None))
        else:
            if not args.vault_path:
                console.print("[error]Error: vault_path must be specified in CLI or pv.toml for local listing.[/error]")
                sys.exit(1)
            list_engine.list_local_snapshots(resolve_path(args.vault_path))

    elif args.command == "push":
        if not args.vault_path:
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)
        if not args.bucket:
            console.print("[error]Error: Bucket must be specified in CLI or pyproject.toml[/error]")
            sys.exit(1)

        key_id, app_key, source = credentials.resolve_credentials(args)

        if not key_id or not app_key:
            console.print("[error]Error: Cloud credentials missing.[/error]")
            console.print("Sources checked: CLI > Doppler > Env > .env > Config")
            console.print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
            sys.exit(1)

        console.print(f"[dim]Authenticated via {source}[/dim]")
        from projectclone import sync_engine
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

    elif args.command == "pull":
        if not args.vault_path:
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)
        if not args.bucket:
            console.print("[error]Error: Bucket must be specified in CLI or pyproject.toml[/error]")
            sys.exit(1)

        key_id, app_key, source = credentials.resolve_credentials(args)

        if not key_id or not app_key:
            console.print("[error]Error: Cloud credentials missing.[/error]")
            console.print("Sources checked: CLI > Doppler > Env > .env > Config")
            console.print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
            sys.exit(1)

        console.print(f"[dim]Authenticated via {source}[/dim]")
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
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)
        from projectclone import integrity_engine
        if not integrity_engine.verify_vault(resolve_path(args.vault_path)):
            sys.exit(1)

    elif args.command == "gc":
        if not args.vault_path:
            console.print("[error]Error: vault_path must be specified in CLI or pv.toml[/error]")
            sys.exit(1)
        from projectclone import gc_engine
        gc_engine.run_garbage_collection(resolve_path(args.vault_path), args.dry_run)

    elif args.command == "config":
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

            # Naive replacement/append for the prototype
            # We assume the user has set the flag, so the section likely exists.
            # We will just append the keys for now or use a regex if we want to be fancy.
            # Simpler: Read lines, find [credentials], update keys if exist, else append.
            
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
            
            # If we didn't find the keys to replace, we need to append them after [credentials]
            # Reread logic: This is complex to get right with just loop.
            # Alternative: Just append to end of file if we know it's enabled.
            # But we want to update if exists.
            
            # Let's stick to the "Security Lock" check being the main value.
            # If passed, we will just append/update.
            # Actually, if the user enabled the flag, they likely have the section.
            
            # Let's rewrite the file with a simplistic parser for now to ensure it works.
            # If keys weren't written but we passed the lock check, just append them to the end.
            if not keys_written["key_id"] or not keys_written["secret_key"]:
                 # Find [credentials] index
                 try:
                     creds_idx = next(i for i, l in enumerate(new_lines) if l.strip() == "[credentials]")
                     # Insert after flag?
                     # If we are here, it means we saw [credentials] but maybe not the keys.
                     # Just append to the section.
                     insert_pos = creds_idx + 1
                     # Find end of section
                     while insert_pos < len(new_lines) and not new_lines[insert_pos].strip().startswith("["):
                         insert_pos += 1
                     
                     if not keys_written["key_id"]:
                         new_lines.insert(insert_pos, f'key_id = "{args.key_id}"')
                         insert_pos += 1
                     if not keys_written["secret_key"]:
                         new_lines.insert(insert_pos, f'secret_key = "{args.secret_key}"')
                 except StopIteration:
                     # Section not found? But we found the flag...
                     # The flag might be commented out or in a weird place, but our string check passed.
                     # Just append to end.
                     new_lines.append("")
                     if not keys_written["key_id"]: new_lines.append(f'key_id = "{args.key_id}"')
                     if not keys_written["secret_key"]: new_lines.append(f'secret_key = "{args.secret_key}"')

            with open(pv_path, "w") as f:
                f.write("\n".join(new_lines) + "\n")
                
            console.print(f"[success]✅ Credentials saved to pv.toml[/success]")
            console.print("[dim]Make sure to exclude this file from version control![/dim]")

    elif args.command == "check-env":
        check_cloud_env()

    elif args.command == "notify-test":
        if notifier:
            console.print("[info]Sending test notification...[/info]")
            notifier.send_message("🔔 Test notification from Project Vault", level="info")
            console.print("[success]Notification sent (check your Telegram).[/success]")
        else:
            console.print("[error]Notifier not initialized. Check your config/env.[/error]")

if __name__ == "__main__":
    main()