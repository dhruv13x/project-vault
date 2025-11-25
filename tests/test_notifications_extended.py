# tests/test_notifications_extended.py

import pytest
from unittest.mock import patch, MagicMock
from src.common.notifications import TelegramNotifier

@patch('rich.console.Console.print')
def test_telegram_notifier_missing_token(mock_print):
    """
    Test that a warning is printed if the bot_token is missing.
    """
    config = {
        "notifications": {
            "telegram": {
                "enabled": True,
                "bot_token": None,
                "chat_id": "12345"
            }
        }
    }
    notifier = TelegramNotifier(config)
    notifier.send_message("Test message")
    mock_print.assert_called_with("[yellow]Warning: Telegram notifications enabled but token/chat_id missing.[/yellow]")

@patch('rich.console.Console.print')
def test_telegram_notifier_missing_chat_id(mock_print):
    """
    Test that a warning is printed if the chat_id is missing.
    """
    config = {
        "notifications": {
            "telegram": {
                "enabled": True,
                "bot_token": "your_token",
                "chat_id": None
            }
        }
    }
    notifier = TelegramNotifier(config)
    notifier.send_message("Test message")
    mock_print.assert_called_with("[yellow]Warning: Telegram notifications enabled but token/chat_id missing.[/yellow]")
