# src/common/hooks.py

import subprocess
import sys
from rich.console import Console

console = Console()

def run_hook(hook_name: str, command: str):
    """
    Executes a shell command defined in the hooks configuration.
    Streams output to the console.

    Args:
        hook_name: The name of the hook (e.g., "pre_snapshot").
        command: The shell command to execute.

    Raises:
        subprocess.CalledProcessError: If the command fails.
    """
    if not command:
        return

    console.print(f"[bold magenta]🪝 Executing {hook_name}:[/bold magenta] [dim]{command}[/dim]")

    try:
        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Stream stdout using iterator form
        # readline() blocks until line is available or EOF ('') is reached
        for line in iter(process.stdout.readline, ''):
            print(f"  | {line.rstrip()}")
            
        # Wait for process to exit and get stderr
        # communicate() reads the rest of stdout (already empty) and all of stderr
        stdout, stderr = process.communicate()
        
        if stderr:
             print(f"  [stderr] {stderr.strip()}")

        if process.returncode != 0:
            console.print(f"[bold red]❌ Hook '{hook_name}' failed with exit code {process.returncode}[/bold red]")
            raise subprocess.CalledProcessError(process.returncode, command)

        console.print(f"[bold green]✔ Hook '{hook_name}' completed.[/bold green]")

    except Exception as e:
        console.print(f"[bold red]❌ Error executing hook '{hook_name}': {e}[/bold red]")
        raise
