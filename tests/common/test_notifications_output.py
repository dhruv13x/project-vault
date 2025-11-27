import pytest
from unittest.mock import MagicMock, patch
from src.common.notifications import TelegramNotifier

class TestTelegramNotifierOutput:
    def test_send_message_missing_token_output(self, capsys):
        config = {"notifications": {"telegram": {"enabled": True}}}
        notifier = TelegramNotifier(config)
        # No token/chat_id set
        notifier.send_message("msg")
        captured = capsys.readouterr()
        # "Warning: Telegram notifications enabled but token/chat_id missing."
        # Rich console prints to stdout usually.
        assert "Warning" in captured.out

    def test_send_message_api_error_output(self, capsys):
        config = {"notifications": {"telegram": {"bot_token": "t", "chat_id": "c", "enabled": True}}}
        notifier = TelegramNotifier(config)

        # Mock API returning 400
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": false}'
        mock_response.status = 400
        mock_urlopen_cm = MagicMock()
        mock_urlopen_cm.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_urlopen_cm):
            notifier.send_message("msg")

        captured = capsys.readouterr()
        assert "Telegram API returned status 400" in captured.out

    def test_send_message_exception_output(self, capsys):
        config = {"notifications": {"telegram": {"bot_token": "t", "chat_id": "c", "enabled": True}}}
        notifier = TelegramNotifier(config)

        with patch("urllib.request.urlopen", side_effect=Exception("Boom")):
            notifier.send_message("msg")

        captured = capsys.readouterr()
        assert "Failed to send Telegram notification: Boom" in captured.out
