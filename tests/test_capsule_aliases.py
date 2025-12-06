import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Mocking argparse
import argparse

def test_capsule_create_alias():
    # We want to verify that `pv capsule create` maps to the same logic as `pv vault`.
    # Since this is an alias at the CLI level, we can test that the parser parses it correctly
    # and that our dispatch logic calls `handle_vault_command`.

    # But since we are calling main(), it's an integration test.
    # Let's mock the handlers in src.cli

    with patch("src.cli.handle_vault_command") as mock_vault:
        from src.cli import main

        # Simulate CLI args
        with patch.object(sys, 'argv', ["pv", "capsule", "create", ".", "my_vault"]):
             # We expect main() to call handle_vault_command
             try:
                 main()
             except SystemExit:
                 pass

             assert mock_vault.called
             args, defaults, notifier = mock_vault.call_args[0]
             assert args.command == "capsule"
             assert args.capsule_command == "create"
             assert args.source == "."
             assert args.vault_path == "my_vault"

def test_capsule_restore_alias():
    with patch("src.cli.handle_vault_restore_command") as mock_restore:
        from src.cli import main

        # Simulate CLI args
        with patch.object(sys, 'argv', ["pv", "capsule", "restore", "manifest.json", "dest_dir"]):
             try:
                 main()
             except SystemExit:
                 pass

             assert mock_restore.called
             args, defaults = mock_restore.call_args[0]
             assert args.manifest == "manifest.json"
             assert args.dest == "dest_dir"
