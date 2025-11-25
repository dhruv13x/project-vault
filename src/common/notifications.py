# src/common/notifications.py

import urllib.request
import json
import os
from rich.console import Console

console = Console()

class TelegramNotifier:
    def __init__(self, config: dict):
        """
        Initialize with a configuration dictionary.
        Expected structure:
        {
            "notifications": {
                "telegram": {
                    "enabled": bool,
                    "bot_token": str,
                    "chat_id": str
                }
            }
        }
        """
        self.enabled = False
        self.bot_token = None
        self.chat_id = None

        tg_config = config.get("notifications", {}).get("telegram", {})
        
        # Support environment variables as override/fallback
        self.bot_token = os.environ.get("PV_TELEGRAM_BOT_TOKEN", tg_config.get("bot_token"))
        self.chat_id = os.environ.get("PV_TELEGRAM_CHAT_ID", tg_config.get("chat_id"))
        self.enabled = tg_config.get("enabled", False)

        # If env vars are present, force enable (unless explicitly disabled in config? No, let's assume env var means intent)
        if self.bot_token and self.chat_id and tg_config.get("enabled") is None:
             self.enabled = True

    def send_message(self, text: str, level: str = "info", silent: bool = False):
        """
        Sends a message to the configured Telegram chat.
        """
        if not self.enabled:
            return

        if not self.bot_token or not self.chat_id:
            if not silent:
                console.print("[yellow]Warning: Telegram notifications enabled but token/chat_id missing.[/yellow]")
            return

        # Add emojis based on level
        emoji = "ℹ️"
        if level == "success":
            emoji = "✅"
        elif level == "warning":
            emoji = "⚠️"
        elif level == "error":
            emoji = "🚨"

        message = f"{emoji} [Project Vault]\n{text}"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        headers = {"Content-Type": "application/json"}
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown" 
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    if not silent:
                        console.print(f"[yellow]Telegram API returned status {response.status}[/yellow]")
        except Exception as e:
            if not silent:
                console.print(f"[yellow]Failed to send Telegram notification: {e}[/yellow]")
