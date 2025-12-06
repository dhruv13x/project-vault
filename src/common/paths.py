# src/common/paths.py

import os
from pathlib import Path

def get_project_name(source_path: str = ".") -> str:
    """
    Determines the project name from the source path (defaulting to CWD).
    Sanitizes the name for filesystem safety.
    """
    abs_source = os.path.abspath(source_path)
    raw_name = os.path.basename(abs_source)
    
    # Sanitize (simple version, can be expanded)
    import re
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_name)
    return clean_name

def get_global_vault_root() -> Path:
    """
    Returns the global root for all Project Vault data: ~/.project_vault
    """
    return Path.home() / ".project_vault"

def get_project_home(project_name: str) -> Path:
    """
    Returns the specific home directory for a project: ~/.project_vault/<project_name>
    """
    return get_global_vault_root() / project_name

def get_default_vault_path(project_name: str = None) -> Path:
    """
    Returns the default CAS vault path: ~/.project_vault/<project_name>/vault
    """
    if not project_name:
        project_name = get_project_name()
    return get_project_home(project_name) / "vault"

def get_default_backup_path(project_name: str = None, backup_type: str = "folder") -> Path:
    """
    Returns the default legacy backup path: 
    - ~/.project_vault/<project_name>/backups (for folders)
    - ~/.project_vault/<project_name>/archive_backups (for archives)
    """
    if not project_name:
        project_name = get_project_name()
    
    folder_name = "archive_backups" if backup_type == "archive" else "backups"
    return get_project_home(project_name) / folder_name

def get_default_restore_destination(project_name: str = None) -> Path:
    """
    Returns the default destination path for restored projects.
    ~/.project_vault/<project_name>/restored_projects
    """
    if not project_name:
        project_name = get_project_name()
    return get_project_home(project_name) / "restored_projects"

