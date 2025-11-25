# tests/test_hooks.py

import unittest
from unittest.mock import patch, MagicMock
import subprocess
from common import hooks

class TestHooks(unittest.TestCase):
    @patch("subprocess.Popen")
    def test_run_hook_success(self, mock_popen):
        # Setup mock process
        process_mock = MagicMock()
        process_mock.stdout.readline.side_effect = ["Output line 1\n", "Output line 2\n", ""]
        process_mock.poll.side_effect = [None, None, 0] # Running, Running, Done
        process_mock.communicate.return_value = (None, None) # no stderr
        process_mock.returncode = 0
        
        mock_popen.return_value = process_mock
        
        hooks.run_hook("test_hook", "echo hello")
        
        mock_popen.assert_called_once()
        self.assertIn("echo hello", mock_popen.call_args[0][0])

    @patch("subprocess.Popen")
    def test_run_hook_failure(self, mock_popen):
        # Setup mock process
        process_mock = MagicMock()
        process_mock.stdout.readline.return_value = ""
        process_mock.poll.return_value = 1
        process_mock.communicate.return_value = (None, "Error message")
        process_mock.returncode = 1
        
        mock_popen.return_value = process_mock
        
        with self.assertRaises(subprocess.CalledProcessError):
            hooks.run_hook("fail_hook", "exit 1")

    def test_run_hook_empty_command(self):
        # Should do nothing and not raise
        hooks.run_hook("empty", "")

if __name__ == "__main__":
    unittest.main()

