# src/common/config.py

import os
import sys

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Warning: 'tomllib' (Python 3.11+) or 'tomli' not found. Config parsing disabled.")
        tomllib = None

def load_project_config(start_path: str = ".") -> dict:
    """
    Loads configuration from pv.toml (priority) or pyproject.toml.

    Args:
        start_path: The directory to search for config files.

    Returns:
        A dictionary containing the configuration.
    """
    if tomllib is None:
        return {}

    # Priority 1: pv.toml (Root-level keys)
    pv_toml_path = os.path.join(start_path, "pv.toml")
    if os.path.exists(pv_toml_path):
        try:
            with open(pv_toml_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse {pv_toml_path}: {e}")
            return {}

    # Priority 2: pyproject.toml (Keys under [tool.project-vault])
    pyproject_path = os.path.join(start_path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data.get("tool", {}).get("project-vault", {})
        except Exception as e:
            print(f"Warning: Failed to parse {pyproject_path}: {e}")
            return {}

    return {}

def generate_init_file(target_path: str = "pv.toml"):
    """
    Generates a template configuration file.

    Args:
        target_path: The path where the file should be created.
    """
    template = """# Project Vault Configuration (pv.toml)

[core]
# Set to false to disable database marker detection suggestions
enable_suggestions = true

# --- Cloud Settings ---
# The name of your B2/S3 Bucket
bucket = "my-project-backups"

# The Endpoint URL (Must include https://)
endpoint = "https://s3.eu-central-003.backblazeb2.com"

# --- Default Paths (Optional) ---
# You can uncomment these to set default vault locations
# vault_path = "./my_vault"
# restore_path = "./restored_project"

# --- Notifications (Optional) ---
# [notifications.telegram]
# enabled = false
# bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
# chat_id = "-1001234567890"

# --- Lifecycle Hooks (Optional) ---
# Commands to run before/after backup and restore.
# [hooks]
# pre_snapshot = "echo 'Snapshot starting...'"
# post_snapshot = "echo 'Snapshot finished.'"
# pre_restore = "echo 'Restore starting...'"
# post_restore = "echo 'Restore finished.'"

# --- Insecure Credentials Storage (Optional) ---
# WARNING: Only enable this on secure, private machines.
# [credentials]
# allow_insecure_storage = false # Set to true to enable
# key_id = "..."
# secret_key = "..."
"""
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(template)
        print(f"✅ Created configuration file at {os.path.abspath(target_path)}")
    except Exception as e:
        print(f"Error creating config file: {e}")
