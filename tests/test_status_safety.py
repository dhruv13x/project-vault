# tests/test_status_safety.py

import pytest
from src.projectclone import status_engine
from unittest.mock import MagicMock, patch

def test_status_same_source_and_vault(tmp_path, capsys):
    """Test that status fails if source and vault are the same."""
    source = tmp_path / "project"
    source.mkdir()
    
    # Mock console to avoid rich output issues or just capture stdout
    # We rely on capsys capturing rich console print if it goes to stdout
    
    status_engine.show_status(str(source), str(source))
    
    captured = capsys.readouterr()
    assert "Source and Vault paths cannot be the same" in captured.out

def test_status_vault_inside_source_not_ignored(tmp_path, capsys):
    """Test that status fails if vault is inside source and NOT ignored."""
    source = tmp_path / "project"
    source.mkdir()
    vault = source / "vault"
    vault.mkdir()
    
    status_engine.show_status(str(source), str(vault))
    
    captured = capsys.readouterr()
    assert "Vault path is inside Source path but not ignored" in captured.out

def test_status_vault_inside_source_ignored(tmp_path, capsys):
    """Test that status succeeds if vault is inside source BUT ignored."""
    source = tmp_path / "project"
    source.mkdir()
    vault = source / "vault"
    vault.mkdir()
    
    # Create .pvignore
    (source / ".pvignore").write_text("vault/")
    
    # We expect it to PROCEED. 
    # Since we didn't mock everything, it might print the header and then "No snapshots found".
    # That proves it passed the safety check.
    
    status_engine.show_status(str(source), str(vault))
    
    captured = capsys.readouterr()
    assert "Project Vault Status" in captured.out
    assert "No snapshots found" in captured.out
