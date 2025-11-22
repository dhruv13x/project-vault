# 🛡️ Project Vault (pv)

> **The Unified, Deduplicated, Cloud-Native Project Lifecycle Manager.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen)]()
[![Storage](https://img.shields.io/badge/Storage-CAS%20Deduplication-orange)]()

**Project Vault** is a professional-grade state management suite designed for developers who need robust, atomic, and efficient project backups. Unlike standard "zip" scripts, Project Vault uses a **Content-Addressable Storage (CAS)** engine—similar to Git or Docker—to deduplicate data, verify integrity, and sync incrementally to the cloud.

---

## 🚀 Key Features

* **📦 CAS Architecture:** Files are stored by their SHA256 hash. Identical files across different snapshots (or different projects!) are stored only once.
* **☁️ Cloud Native:** Incremental, bidirectional synchronization with **Backblaze B2** (and S3-compatible endpoints).
* **🛡️ Zero-Trust Restoration:** The restore engine validates every path to prevent directory traversal attacks or symlink exploits.
* **⚡ Smart Ignore:** Automatically respects `.vaultignore` patterns to skip `node_modules`, `__pycache__`, and other junk.
* **🔍 Integrity Verification:** Built-in "Bit Rot" detection. Scans your vault to ensure no file has been corrupted or tampered with.
* **🔄 Disaster Recovery:** `pv pull` allows you to restore your entire project history from the cloud to a fresh machine with one command.

---

## 🛠️ Installation

Project Vault is designed to be installed as a system-wide tool (`pv`).

```bash
# 1. Clone the repository
git clone [https://github.com/dhruv13x/project-vault.git](https://github.com/dhruv13x/project-vault.git)
cd project_vault

# 2. Install in editable mode (Development)
pip install -e .

Verify the installation:
pv --help

📖 Usage Guide
1. Creating a Backup (The Vault)
Create a deduplicated snapshot of your project.
# Usage: pv vault <source_dir> <vault_dir>
pv vault . /sdcard/backups/my_vault

 * Note: This will create a JSON manifest in snapshots/ and store unique files in objects/.
 * Ignoring Files: Create a .vaultignore file in your source directory to skip specific files (uses .gitignore syntax).
2. Cloud Synchronization (Push)
Upload your local vault to the cloud. Uses Incremental Sync—only missing objects are uploaded.
Prerequisites:
Export your Backblaze B2 credentials:
export B2_KEY_ID="your_key_id"
export B2_APP_KEY="your_app_key"

Command:
# Usage: pv sync <vault_dir> --bucket <bucket_name> --endpoint <url>
pv sync /sdcard/backups/my_vault \
  --bucket project-vault-backups \
  --endpoint [https://s3.eu-central-003.backblazeb2.com](https://s3.eu-central-003.backblazeb2.com)

3. Disaster Recovery (Pull)
Download missing history from the cloud. Perfect for setting up a new machine or recovering deleted snapshots.
pv pull /sdcard/backups/my_vault \
  --bucket project-vault-backups \
  --endpoint [https://s3.eu-central-003.backblazeb2.com](https://s3.eu-central-003.backblazeb2.com)

4. Restoring a Project
Restore a specific point-in-time snapshot to a working directory.
# Usage: pv vault-restore <manifest_path> <destination>
pv vault-restore \
  /sdcard/backups/my_vault/snapshots/snapshot_2025-11-22T10-00.json \
  /sdcard/projects/restored_app

5. Integrity Check
Scan the vault for corruption. This calculates the SHA256 hash of every object and ensures it matches its filename.
pv check-integrity /sdcard/backups/my_vault

Output: ✅ OK or ❌ CORRUPTION DETECTED
6. Environment Check
Verify your B2 credentials are correctly set in your environment.
pv b2-check

### 7. Garbage Collection (Maintenance)
Cleanup orphaned data. If you delete old snapshots, the underlying objects stay in the vault. This command scans the vault and deletes any object not referenced by an active snapshot.

```bash
# Preview what will be deleted (Safe Mode)
pv gc /sdcard/backups/my_vault --dry-run

# Actually delete orphaned files
pv gc /sdcard/backups/my_vault


🏗️ Architecture
Project Vault uses a Monorepo structure with a shared core library.
project_vault/
├── pyproject.toml       # Build configuration & Dependency management
├── src/
│   ├── cli.py           # Main Entry Point (Dispatcher)
│   ├── common/          # Shared Logic (CAS, B2, S3, Ignore, Manifests)
│   └── ...
├── projectclone/        # Backup Engine
│   └── src/projectclone/
│       ├── cas_engine.py   # The Deduplication Logic
│       ├── sync_engine.py  # The Cloud Sync Logic
│       └── integrity_engine.py
└── projectrestore/      # Restore Engine
    └── src/projectrestore/
        └── restore_engine.py # The Zero-Trust Restoration Logic

🔐 Security Model
 * Credentials: Credentials are never stored in files or arguments. They are read strictly from environment variables (B2_KEY_ID, B2_APP_KEY) to prevent accidental git commits.
 * Path Validation: The restore engine rejects absolute paths (/etc/passwd) and directory traversal (../../) to prevent malicious archives from overwriting system files.
 * Hash Verification: Files are addressed by content. It is mathematically impossible to retrieve the "wrong" version of a file if the hash matches.
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
