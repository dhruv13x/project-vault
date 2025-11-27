import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.common.notifications import TelegramNotifier

class TestTelegramNotifier:
    def test_init_missing_config(self):
        notifier = TelegramNotifier({})
        assert notifier.enabled is False

    def test_init_success(self):
        # Config structure matches src/common/notifications.py
        config = {"notifications": {"telegram": {"bot_token": "token", "chat_id": "id", "enabled": True}}}
        notifier = TelegramNotifier(config)
        assert notifier.enabled is True
        assert notifier.bot_token == "token"
        assert notifier.chat_id == "id"

    def test_send_message_disabled(self):
        notifier = TelegramNotifier({})
        with patch("urllib.request.urlopen") as mock_url:
            notifier.send_message("msg")
            mock_url.assert_not_called()

    def test_send_message_success(self):
        config = {"notifications": {"telegram": {"bot_token": "token", "chat_id": "id", "enabled": True}}}
        notifier = TelegramNotifier(config)

        # Mock the response object returned by urlopen context manager
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.status = 200

        mock_urlopen_cm = MagicMock()
        mock_urlopen_cm.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_urlopen_cm) as mock_url:
            notifier.send_message("msg")
            mock_url.assert_called()

    def test_send_message_exception(self):
        config = {"notifications": {"telegram": {"bot_token": "token", "chat_id": "id", "enabled": True}}}
        notifier = TelegramNotifier(config)
        with patch("urllib.request.urlopen", side_effect=Exception("Net Fail")):
            # Should not raise
            notifier.send_message("msg")

    def test_send_message_levels(self):
        config = {"notifications": {"telegram": {"bot_token": "token", "chat_id": "id", "enabled": True}}}
        notifier = TelegramNotifier(config)

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"ok": true}'
        mock_response.status = 200
        mock_urlopen_cm = MagicMock()
        mock_urlopen_cm.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_urlopen_cm) as mock_url:
            notifier.send_message("msg", level="error")
            # Check calls
            assert mock_url.called
