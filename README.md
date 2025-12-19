# Project Vault (pv) 🏦

> **The Unified Project Lifecycle Manager: Backup, Restore, and Teleport Projects Anywhere.**

<div align="center">
  <img src="https://raw.githubusercontent.com/dhruv13x/project-vault/main/project-vault_logo.png" alt="Project Vault Logo" width="200"/>
</div>

<div align="center">

[![Build Status](https://img.shields.io/github/actions/workflow/status/dhruv13x/project-vault/test.yml?branch=main)](https://github.com/dhruv13x/project-vault/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linting-ruff-yellow.svg)](https://github.com/astral-sh/ruff)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/dhruv13x/project-vault/graphs/commit-activity)

</div>

**Project Vault (pv)** is your command-line companion for managing project state. It combines the power of atomic backups, cloud synchronization, and time-travel restoration into a single, unified tool. Think of it as **Time Machine for your dev projects** — portable, reproducible, and cloud-ready.

---

## ⚡ Quick Start (The "5-Minute Rule")

### Prerequisites
-   **Python 3.10+**
-   **Pip** (Python Package Installer)
-   **Docker** (Optional, for database backups)

### Installation

```bash
# Clone the repository
git clone https://github.com/dhruv13x/project-vault.git
cd project-vault

# Install in editable mode
pip install -e .[dev]
pip install -e ./projectclone
pip install -e ./projectrestore
```

### Run

Verify the installation:

```bash
pv --version
```

### Demo

Create a snapshot of your current project and list it:

```bash
# 1. Initialize (optional, for auto-ignore)
pv init --smart

# 2. Create a local snapshot
pv vault . --name "initial-commit"

# 3. List snapshots
pv list
```

---

## ✨ Features

### 🛡️ Core Reliability
-   **Atomic Snapshots**: Never lose data due to a partial backup. Snapshots are verified and immutable.
-   **Content Addressable Storage (CAS)**: Deduplication at the file level. Save space by storing unique files only once.
-   **Symlink Support**: Preserves symlinks (or optionally follows them), ensuring complex project structures remain intact.

### 🚀 Performance
-   **ZStandard Compression**: High-speed, high-ratio compression for efficient storage and transfer.
-   **Incremental Backups**: Only changed files are processed, making subsequent backups lightning fast.

### ☁️ Cloud & Security
-   **Cloud Sync (S3/B2)**: Push and pull your vaults to any S3-compatible storage.
-   **Encrypted Configuration**: Securely handle credentials (optional integration).
-   **Integrity Checks**: Verify the health of your local vault and cloud storage.

### 🧩 Developer Experience
-   **TUI (Textual UI)**: Browse snapshots and restore files using an interactive terminal interface (`pv browse`).
-   **Smart Ignorance**: Auto-generates `.pvignore` based on project type (Python, Node, Rust, etc.).
-   **Rich Output**: Beautiful, color-coded terminal output using `rich`.

---

## 🛠️ Configuration

Project Vault can be configured via environment variables, a local `pv.toml`, or `pyproject.toml`.

### Environment Variables

| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `PV_BUCKET` | The default cloud bucket name. | None | No (unless pushing) |
| `PV_ENDPOINT` | The S3-compatible endpoint URL. | None | No (unless pushing) |
| `PV_VAULT_PATH` | Default local path to store the vault. | `~/.project-vault` | No |
| `PV_RESTORE_PATH` | Default path to restore projects. | `./restored` | No |
| `PV_TELEGRAM_BOT_TOKEN` | Telegram Bot Token for notifications. | None | No |
| `PV_TELEGRAM_CHAT_ID` | Telegram Chat ID for notifications. | None | No |
| `PV_DB_PASSWORD` | Database password for backups. | None | No |

### CLI Arguments

Common arguments for `pv vault` (create snapshot):

| Flag | Description |
| :--- | :--- |
| `--name` | Tag the snapshot with a custom name. |
| `--cloud` | Push to cloud immediately after creating. |
| `--symlinks` | Preserve symlinks instead of copying targets. |
| `--bucket` | Override configured bucket. |
| `--endpoint` | Override configured endpoint. |
| `--include-db` | Include database snapshot in the backup. |

Common arguments for `pv list`:

| Flag | Description |
| :--- | :--- |
| `--cloud` | List snapshots from the cloud instead of local. |
| `--limit` | Number of snapshots to show (default: 10). |

---

## 🏗️ Architecture

Project Vault follows a monorepo structure, orchestrating specialized engines for backup (`projectclone`) and restore (`projectrestore`).

### Directory Tree

```text
project-vault/
├── src/                        # Main CLI and Orchestration Logic
│   ├── cli.py                  # Entry Point (pv)
│   ├── cli_dispatch.py         # Command Routing
│   ├── common/                 # Shared Utilities (Config, Crypto, S3/B2)
│   ├── tui.py                  # Textual User Interface
│   └── projectvault/           # Database & Engine Logic
├── projectclone/               # Backup Engine (Snapshot Creation)
│   └── src/projectclone/       # Core Backup Logic
├── projectrestore/             # Restore Engine (Snapshot Application)
    └── src/projectrestore/     # Core Restore Logic
```

### Data Flow

1.  **Input**: User runs `pv vault` in a project directory.
2.  **Filter**: `src/common/ignore.py` applies `.pvignore` rules.
3.  **Capture**: `projectclone` scans files, computes hashes, and stores unique objects in the CAS (Content Addressable Storage).
4.  **Manifest**: A JSON manifest is created, linking file paths to CAS objects.
5.  **Sync (Optional)**: `pv push` uploads new CAS objects and the manifest to the configured Cloud Storage (S3/B2).
6.  **Restore**: `pv vault-restore` (or `projectrestore`) reads the manifest, fetches objects from CAS, and reconstructs the directory state.

---

## 🐞 Troubleshooting

### Common Issues

| Error Message | Possible Cause | Solution |
| :--- | :--- | :--- |
| `B2ConnectionError` / `403` | Invalid credentials or endpoint. | Check `pv.toml` or `PV_ENDPOINT`. Ensure keys are correct. |
| `Snapshot not found` | Local vault is empty or path is wrong. | Run `pv list` to see available snapshots. Check `PV_VAULT_PATH`. |
| `Permission denied` | Lack of write access to vault/restore path. | Ensure you have permissions for the directory. |
| `Docker not found` | Docker daemon not running. | Start Docker if using `pv db` or `--include-db`. |

### Debug Mode

To enable verbose logging and see stack traces, you can run the CLI module directly:

```bash
# Run with python directly for detailed tracebacks
python3 src/cli.py [command]
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started, report bugs, or suggest features.

### Dev Setup

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/dhruv13x/project-vault
    cd project-vault
    # Install main package and sub-packages in editable mode
    pip install -e .[dev]
    pip install -e ./projectclone
    pip install -e ./projectrestore
    ```

2.  **Run Tests**:
    ```bash
    python3 -m pytest
    ```

---

## 🗺️ Roadmap

- [ ] **Encryption**: Client-side encryption for zero-knowledge cloud backups.
- [ ] **Daemon Mode**: Background watcher for auto-backups on file change.
- [ ] **Web UI**: A lightweight web interface for browsing vaults remotely.
- [ ] **Plugin System**: Hooks for custom pre/post backup actions (e.g., database dumps).

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/dhruv13x">Dhruv13x</a></sub>
</div>
