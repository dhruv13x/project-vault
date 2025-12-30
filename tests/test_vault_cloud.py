# tests/test_vault_cloud.py

import argparse
import pytest
from unittest.mock import MagicMock, patch
from src.cli_dispatch import handle_vault_command

@pytest.fixture
def mock_args():
    args = MagicMock()
    args.vault_path = "/vault"
    args.source = "/source"
    args.name = "test_proj"
    args.symlinks = False
    args.cloud = True
    args.bucket = "test-bucket"
    args.endpoint = None
    args.dry_run = False
    return args

@pytest.fixture
def mock_credentials():
    creds = MagicMock()
    creds.resolve_credentials.return_value = ("key", "secret", "Test")
    return creds

def test_vault_cloud_sync_triggered(mock_args, mock_credentials):
    """Test that sync_to_cloud is called when --cloud is passed to vault."""
    
    with patch("src.projectclone.cas_engine.backup_to_vault") as mock_backup, \
         patch("src.projectclone.sync_engine.sync_to_cloud") as mock_sync, \
         patch("src.common.console.console.print"):
        
        mock_backup.return_value = "/vault/manifest.json"
        
        handle_vault_command(mock_args, defaults={}, notifier=None, credentials_module=mock_credentials)
        
        # Verify backup called
        mock_backup.assert_called_once()
        
        # Verify sync called
        mock_sync.assert_called_once()
        # Check args: vault_path, bucket, endpoint, key, secret, dry_run
        call_args = mock_sync.call_args
        assert call_args[0][0] == "/vault" # path is resolved in implementation but mock input is absolute-ish
        assert call_args[0][1] == "test-bucket"
        assert call_args[0][3] == "key"

def test_vault_cloud_missing_bucket(mock_args, mock_credentials):
    """Test error message if bucket is missing."""
    mock_args.bucket = None
    
    with patch("src.projectclone.cas_engine.backup_to_vault") as mock_backup, \
         patch("src.projectclone.sync_engine.sync_to_cloud") as mock_sync, \
         patch("src.common.console.console.print") as mock_print:
        
        handle_vault_command(mock_args, defaults={}, notifier=None, credentials_module=mock_credentials)
        
        mock_backup.assert_called_once()
        mock_sync.assert_not_called()
        
        # Verify error printed
        found = False
        for call in mock_print.call_args_list:
            if "bucket must be specified" in str(call):
                found = True
                break
        assert found
