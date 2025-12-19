from rich.panel import Panel
from rich.text import Text
import argparse
from src.common.console import console

# --- Help Panel Functions ---

def print_vault_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv vault[/] [yellow][source] [vault_path][/] [magenta][--name <name>]

Creates a content-addressable snapshot of the [yellow]source[/] directory (default: current dir) into the [yellow]vault_path[/].

[bold]Arguments:[/bold]
  [yellow]source[/]          Source directory to back up. Defaults to '.'.
  [yellow]vault_path[/]      Destination vault directory. Can be set in config.
  [yellow]--name <name>[/]    Set a custom project name for the snapshot.
  [yellow]--symlinks[/]      Preserve symlinks as links (default: follow them).
  [yellow]--cloud[/]         Push the vault content to cloud storage immediately.
  [yellow]--bucket <B>[/]     Cloud bucket name (required if --cloud is used).
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

def print_capsule_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv capsule[/] [yellow]<subcommand>[/] [magenta][<args>...][/]

Manage project capsules (snapshots).

[bold]Subcommands:[/bold]
  [cyan]create[/cyan]          Create a new capsule (alias for `pv vault`).
  [cyan]restore[/cyan]         Restore a capsule (alias for `pv vault-restore`).

[bold]Arguments:[/bold]
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv capsule`[/]", border_style="blue"))

def print_verify_clone_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv verify-clone[/] [yellow]<original_path> <clone_path>[/]

Walks both directory trees and verifies bit-identical content.
Proves that the capsule restoration was perfect.

[bold]Arguments:[/bold]
  [yellow]original_path[/]    The original source directory.
  [yellow]clone_path[/]       The restored (cloned) directory.
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv verify-clone`[/]", border_style="blue"))

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

def print_db_help():
    console.print(Panel(Text.from_markup("""
[bold green]Usage:[/] [cyan]pv db[/] [yellow]<subcommand>[/] [magenta][<args>...][/]

Manage database snapshots linked to your project.

[bold]Subcommands:[/bold]
  [cyan]backup[/cyan]          Create a snapshot of the configured database.
  [cyan]restore[/cyan]         Restore the database from a specific snapshot.

[bold]Arguments:[/bold]
  [yellow]-h, --help[/]        Show this help message.
"""), title="[bold]Help: `pv db`[/]", border_style="blue"))

def print_main_help():
    """Prints the main help panel using rich."""
    grid = Text.from_markup(
        """
[bold green]Usage:[/] [cyan]pv[/] [yellow]<command>[/] [magenta][<args>...][/]

[bold green]Core Commands[/bold green]
  [cyan]backup[/cyan]          Create a new backup of a project (legacy file-based).
  [cyan]archive-restore[/cyan] Restore a project from a legacy file-based backup.
  [cyan]vault[/cyan]           Create a new content-addressable snapshot of a project.
  [cyan]vault-restore[/cyan]   Restore a project from a vault snapshot.
  [cyan]capsule[/cyan]         Alias for vault operations (create/restore).
  [cyan]db[/cyan]              Manage database snapshots.
  [cyan]verify-clone[/cyan]    Verify that a restored project is identical to the source.

[bold green]Cloud Commands[/bold green]
  [cyan]push[/cyan]            Push vault contents to cloud storage (S3/B2).
  [cyan]pull[/cyan]            Pull vault contents from cloud storage.
  [cyan]list --cloud[/cyan]    List snapshots available in the cloud.

[bold green]Local & Maintenance Commands[/bold green]
  [cyan]status[/cyan]          Show workspace and vault status vs last snapshot.
  [cyan]list[/cyan]            List local snapshots.
  [cyan]diff[/cyan]            Show changes between workspace and a file in the snapshot.
  [cyan]checkout[/cyan]        Restore a specific file from the last snapshot.
  [cyan]gc[/cyan]              Clean up orphaned objects from the vault.
  [cyan]check-integrity[/cyan] Verify the integrity of the local vault.
  [cyan]init[/cyan]            Create a default `pv.toml` configuration file.
  [cyan]check-env[/cyan]       Verify cloud environment variables are set.

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


# --- Custom Argparse Actions ---

class RichVaultHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_vault_help(); p.exit()

class RichVaultRestoreHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_vault_restore_help(); p.exit()

class RichCapsuleHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_capsule_help(); p.exit()

class RichVerifyCloneHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_verify_clone_help(); p.exit()

class RichPushHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_push_help(); p.exit()

class RichPullHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_pull_help(); p.exit()

class RichListHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_list_help(); p.exit()

class RichDbHelpAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs): super().__init__(option_strings, dest, nargs=0, **kwargs)
    def __call__(self, p, n, v, o=None): print_db_help(); p.exit()

class RichHelpAction(argparse.Action):
    """
    A custom argparse action to show a rich-formatted help panel and exit.
    """
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print_main_help()
        parser.exit()
