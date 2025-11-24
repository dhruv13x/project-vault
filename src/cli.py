#!/usr/bin/env python3
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

import pdb # Added for debugging

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
    import pv_core.config as config
except ImportError:
    # Fallback: try relative import if running as script/module inside src
    try:
        from pv_core import config
    except ImportError:
        # Final fallback for some editable installs or specific layouts
        try:
            from src.pv_core import config
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

    console.print(Panel("🔮 Doppler Token detected. Fetching secrets...", title="Doppler Integration", border_style="cyan"))

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
            
            console.print(f"[success]✅ Loaded {count} secrets from Doppler.[/success]")
    except Exception as e:
        console.print(f"[error]❌ Failed to load Doppler secrets: {e}[/error]")


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
    status_text = Text()
    
    # Check B2
    b2_key_pv = os.environ.get("PV_B2_KEY_ID")
    b2_app_pv = os.environ.get("PV_B2_APP_KEY")
    b2_key_std = os.environ.get("B2_KEY_ID")
    b2_app_std = os.environ.get("B2_APP_KEY")
    
    if b2_key_pv and b2_app_pv:
        status_text.append("✅ Found PV-prefixed B2 Credentials (PV_B2_KEY_ID, PV_B2_APP_KEY)\n", style="success")
    elif b2_key_std and b2_app_std:
        status_text.append("✅ Found Standard B2 Credentials (B2_KEY_ID, B2_APP_KEY)\n", style="success")
    else:
        status_text.append("⚠️  Missing B2 Credentials\n", style="warning")

    # Check AWS/S3
    aws_key_pv = os.environ.get("PV_AWS_ACCESS_KEY_ID")
    aws_secret_pv = os.environ.get("PV_AWS_SECRET_ACCESS_KEY")
    aws_key_std = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_std = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    if aws_key_pv and aws_secret_pv:
        status_text.append("✅ Found PV-prefixed AWS/S3 Credentials (PV_AWS_ACCESS_KEY_ID, PV_AWS_SECRET_ACCESS_KEY)\n", style="success")
    elif aws_key_std and aws_secret_std:
        status_text.append("✅ Found Standard AWS/S3 Credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)\n", style="success")
    else:
        status_text.append("⚠️  Missing AWS/S3 Credentials\n", style="warning")

    if not (b2_key_pv or b2_key_std) and not (aws_key_pv or aws_key_std):
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
    # 1. Inject Doppler Secrets (Environment Override)
    inject_doppler_secrets()

    # 2. Load File Config
    defaults = config.load_project_config()
    
    # Initialize Notifier
    try:
        from pv_core.notifications import TelegramNotifier
        notifier = TelegramNotifier(defaults)
    except ImportError:
        # Fallback if running in different context
        try:
            from pv_core.notifications import TelegramNotifier
            notifier = TelegramNotifier(defaults)
        except ImportError:
            notifier = None

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
            
            key_id, app_key = get_credentials()

            if not key_id or not app_key:
                console.print("[error]Error: Cloud credentials missing.[/error]")
                console.print("Set PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (preferred) or standard AWS_.../B2_... variables.")
                sys.exit(1)
            
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

        key_id, app_key = get_credentials()

        if not key_id or not app_key:
            console.print("[error]Error: Cloud credentials missing.[/error]")
            console.print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
            sys.exit(1)

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

        key_id, app_key = get_credentials()

        if not key_id or not app_key:
            console.print("[error]Error: Cloud credentials missing.[/error]")
            console.print("Please export PV_AWS_ACCESS_KEY_ID/PV_AWS_SECRET_ACCESS_KEY (for S3) or B2 equivalent.")
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
