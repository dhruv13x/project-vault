# tests/test_capsule_aliases.py

import sys
import os
from unittest.mock import patch, MagicMock
import pytest
from src.cli import main

def test_capsule_create_alias(capsys):
    """Test that `pv capsule create` maps to `pv vault`."""
    test_args = ["pv", "capsule", "create", "source_dir", "dest_dir"]
    
    # Mock handle_vault_command to verify it gets called
    with patch("src.cli.handle_vault_command") as mock_vault:
        with patch.object(sys, 'argv', test_args):
            main()
            
        mock_vault.assert_called_once()
        # Check args passed to handler
        args, defaults, notifier, creds = mock_vault.call_args[0]
        assert args.source == "source_dir"
        assert args.vault_path == "dest_dir"

def test_capsule_restore_alias(capsys):
    """Test that `pv capsule restore` maps to `pv vault-restore`."""
    test_args = ["pv", "capsule", "restore", "manifest.json", "dest_dir"]
    
    with patch("src.cli.handle_vault_restore_command") as mock_restore:
        with patch.object(sys, 'argv', test_args):
            main()
            
        mock_restore.assert_called_once()
        args, defaults = mock_restore.call_args[0]
        assert args.manifest == "manifest.json"
        assert args.dest == "dest_dir"