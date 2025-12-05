from rich.console import Console
from rich.theme import Theme

# Define custom theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "command": "bold magenta",
})
console = Console(theme=custom_theme)
