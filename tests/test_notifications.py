# tests/test_notifications.py

import unittest
from unittest.mock import patch, MagicMock
import json
import urllib.error

from common.notifications import TelegramNotifier

class TestTelegramNotifier(unittest.TestCase):
    def test_init_disabled(self):
        config = {}
        notifier = TelegramNotifier(config)
        self.assertFalse(notifier.enabled)

    def test_init_config_enabled(self):
        config = {
            "notifications": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "token",
                    "chat_id": "123"
                }
            }
        }
        notifier = TelegramNotifier(config)
        self.assertTrue(notifier.enabled)
        self.assertEqual(notifier.bot_token, "token")
        self.assertEqual(notifier.chat_id, "123")

    def test_init_env_override(self):
        config = {}
        with patch.dict("os.environ", {"PV_TELEGRAM_BOT_TOKEN": "env_token", "PV_TELEGRAM_CHAT_ID": "env_chat"}):
            notifier = TelegramNotifier(config)
            self.assertTrue(notifier.enabled) # Should auto-enable if env vars present
            self.assertEqual(notifier.bot_token, "env_token")
            self.assertEqual(notifier.chat_id, "env_chat")

    @patch("urllib.request.urlopen")
    def test_send_message_success(self, mock_urlopen):
        config = {
            "notifications": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "token",
                    "chat_id": "123"
                }
            }
        }
        notifier = TelegramNotifier(config)
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        notifier.send_message("Hello World")
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://api.telegram.org/bottoken/sendMessage")
        
        data = json.loads(req.data)
        self.assertEqual(data["chat_id"], "123")
        self.assertIn("Hello World", data["text"])

    @patch("urllib.request.urlopen")
    def test_send_message_disabled(self, mock_urlopen):
        config = {} # Disabled by default
        notifier = TelegramNotifier(config)
        notifier.send_message("Should not send")
        mock_urlopen.assert_not_called()

if __name__ == "__main__":
    unittest.main()
