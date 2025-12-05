<div align="center">
  <img src="https://raw.githubusercontent.com/dhruv13x/project-vault/main/project-vault_logo.png" alt="project-vault logo" width="200"/>
</div>

<div align="center">

<!-- Package Info -->
[![PyPI version](https://img.shields.io/pypi/v/project-vault.svg)](https://pypi.org/project/project-vault/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
![Wheel](https://img.shields.io/pypi/wheel/project-vault.svg)
[![Release](https://img.shields.io/badge/release-PyPI-blue)](https://pypi.org/project/project-vault/)

<!-- Build & Quality -->
[![Build status](https://github.com/dhruv13x/project-vault/actions/workflows/publish.yml/badge.svg)](https://github.com/dhruv13x/project-vault/actions/workflows/publish.yml)
[![Codecov](https://codecov.io/gh/dhruv13x/project-vault/graph/badge.svg)](https://codecov.io/gh/dhruv13x/project-vault)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen.svg)](https://github.com/dhruv13x/project-vault/actions/workflows/test.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linting-ruff-yellow.svg)](https://github.com/astral-sh/ruff)
![Security](https://img.shields.io/badge/security-CodeQL-blue.svg)

<!-- Usage -->
![Downloads](https://img.shields.io/pypi/dm/project-vault.svg)
[![PyPI Downloads](https://img.shields.io/pypi/dm/project-vault.svg)](https://pypistats.org/packages/project-vault)
![OS](https://img.shields.io/badge/os-Linux%20%7C%20macOS%20%7C%20Windows-blue.svg)
[![Python Versions](https://img.shields.io/pypi/pyversions/project-vault.svg)](https://pypi.org/project/project-vault/)

<!-- License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>


# Project Vault (pv)

**The Unified Project Lifecycle Manager.**  
Teleport your entire project state—code, databases, caches, and environments—anywhere, safely.

---

## 🚀 The Core Vision

Project Vault (`pv`) creates **100% identical project capsules**. It captures the "messy reality" of a working project that Git ignores: local databases, `node_modules`, `.env` files, compiled binaries, and temp directories.

If you restore a `pv` snapshot on a new machine and run `diff -r`, you will see **zero differences**.

**Use Cases:**
*   **Teleport:** Move a running workspace from Laptop → Server in seconds.
*   **Resurrect:** Restore a dead environment exactly as it was 3 months ago.
*   **Debug:** Snapshot a bug state (including the DB) and send it to a colleague.

---

## 📦 Installation

### The Full Suite (Recommended)
Install the unified tool to get backup, restore, and cloud synchronization features.

```bash
pip install project-vault
```

This installs the `pv` command, which includes:
*   **`projectclone`**: The core snapshot engine.
*   **`projectrestore`**: The safety-critical restoration tool.
*   An interactive TUI for browsing snapshots (powered by `textual`).

### Standalone Tools (Advanced)
For servers, CI/CD, or minimal environments, you can install the components independently:

*   **Backup Only:** `pip install projectclone` (No cloud deps)
*   **Restore Only:** `pip install projectrestore` (Zero dependencies, ultra-lightweight)

---

## ✨ Key Features

*   **Interactive Time Machine**: **(God Level)** Browse, view, and restore files from any snapshot in a terminal-based UI (`pv browse`).
*   **Cloud Agnostic Sync**: Push/pull encrypted, deduplicated snapshots to AWS S3, Backblaze B2, or any S3-compatible storage.
*   **Content-Addressable Storage**: Every file is stored once, saving space and ensuring data integrity.
*   **Lifecycle Hooks**: Execute pre/post-backup and pre/post-restore shell commands for seamless integration with databases and services.
*   **Vault Garbage Collection**: Clean up orphaned data blocks from the vault with the `pv gc` command.
*   **Environment Checker**: The `pv check-env` command verifies your cloud credentials and dependencies.
*   **Notification Integration**: Test your notification setup with `pv notify-test`.
*   **Doppler Secret Integration**: Automatically inject secrets from Doppler for secure cloud access.
*   **Symlink Support**: Fully supports backing up and restoring symbolic links as first-class objects.

---

## ⚡ Quick Start

### 1. Initialize
Run this in your project root to generate a config file (`pv.toml`).
```bash
pv init
```

### 2. Create a Snapshot
Capture the current state of your project into the local vault.
```bash
pv vault
```

### 3. Check Status
See what has changed in your workspace since the last snapshot.
```bash
pv status
```

### 4. Sync to Cloud
Push your encrypted, deduplicated snapshots to S3 or Backblaze B2.
```bash
# Preview what will be uploaded
pv push --dry-run

# Upload
pv push
```

### 5. Restore (Teleport)
Bring the project back to life on any machine.
```bash
# Restore the entire project
pv vault-restore ./vault/snapshots/my-project/snapshot_latest.json ./restored_project

# Or fix a single mistake locally
pv checkout src/main.py
```

---

## 🛠️ Commands

| Command | Description |
| :--- | :--- |
| `pv browse` | **(God Level)** Interactive TUI to browse, view, and restore from snapshots. |
| `pv vault` | Create a content-addressable snapshot of the current directory. |
| `pv vault-restore` | Full project restoration from a manifest. |
| `pv status` | Show modified files and cloud sync status. |
| `pv diff` | Compare a local file against the latest snapshot. |
| `pv checkout` | Restore a specific file from the latest snapshot. |
| `pv push` | Sync local vault to Cloud (S3/B2). |
| `pv pull` | Download missing snapshots from Cloud. |
| `pv list` | List all local or cloud snapshots. |
| `pv gc` | Run garbage collection to clean up orphaned vault objects. |
| `pv check-integrity`| Verify the health of the local vault (detect corruption). |
| `pv check-env` | Check cloud credentials and dependencies. |
| `pv notify-test` | Send a test notification. |
| `pv config set-creds` | Save credentials to `pv.toml` (requires manual security override). |
| `pv init` | Create a default `pv.toml` configuration file. Use `--smart` to auto-detect project type and generate `.pvignore`. |
| `pv backup` | (Legacy) Create a file-based backup. |
| `pv archive-restore` | (Legacy) Restore a file-based backup. |

---

## 🖥️ Interactive TUI (`pv browse`)

For a "Time Machine"-like experience, run the `browse` command. This opens a Textual-based UI that lets you:

*   Navigate all historical snapshots for a project.
*   Expand snapshots to see the full file tree.
*   View the contents of any file from a past version.
*   Restore a single file by pressing `r`.

```
$ pv browse

┌─ Snapshots: my-api ──────────────────────────────────────────┐
│ ┌─ 20231125_120000 ────────────────────────────────────────── │
│ │  📁 src/                                                   │
│ │  │  📄 main.py                                             │
│ │  │  📄 routes.py                                           │
│ │  📄 .env                                                    │
│ │  📄 README.md                                               │
│ └─ 20231124_183000 ────────────────────────────────────────── │
│    ...                                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration & Advanced Usage

### Configuration File (`pv.toml`)
Running `pv init` creates a `pv.toml` file for project-specific settings. You can also define these in your `pyproject.toml` under the `[tool.project-vault]` section.

Key options:
- `bucket`: The default cloud bucket.
- `endpoint`: The S3-compatible endpoint URL.
- `vault_path`: The local directory to store vault data.
- `restore_path`: The default directory for `vault-restore`.

### Environment Variables & Precedence
`pv` uses a clear hierarchy for resolving settings:

1.  **Command-Line Flags**: Arguments like `--bucket my-bucket` always win.
2.  **`PV_` Prefixed Env Vars**: `PV_BUCKET` overrides `BUCKET` from a file.
3.  **Doppler Secrets**: If `DOPPLER_TOKEN` is set, secrets are fetched and injected as environment variables.
4.  **Standard Env Vars**: `AWS_ACCESS_KEY_ID`, `B2_KEY_ID`, etc.
5.  **Config File**: `pv.toml` or `pyproject.toml` values are used last.

> **Security Note**
> For automated environments, using Doppler or `PV_` prefixed variables is highly recommended to avoid leaking general-purpose cloud credentials.

### Lifecycle Hooks
You can define shell commands in your `pv.toml` to run at critical stages of the backup/restore process. This is ideal for dumping a database before backup or restarting a service after restore.

```toml
[tool.project-vault.hooks]
pre-backup = "pg_dump my_db > backup.sql"
post-restore = "psql my_db < backup.sql && rm backup.sql"
```

---

## 🏗️ Architecture

Project Vault is a **monorepo** containing three distinct tools:

```text
.
├── src/                  # The 'pv' Orchestrator & CLI
│   ├── cli.py            # Main entry point
│   ├── tui.py            # Textual-based Time Machine
│   └── common/           # Shared utilities (config, credentials, hooks)
├── projectclone/         # The Backup Engine
│   └── src/
│       ├── cas_engine.py # Content-Addressable Storage logic
│       └── sync_engine.py# Cloud synchronization (S3/B2)
└── projectrestore/       # The Restore Engine
    └── src/
        └── restore_engine.py # Safety-critical restoration logic
```

1.  **`project-vault` (pv):** The orchestrator. Handles configuration, cloud sync, and user interaction.
2.  **`projectclone`:** The backup engine. Handles hashing, deduplication, and manifest generation.
3.  **`projectrestore`:** The restore engine. A standalone, dependency-free tool focused purely on safe data reconstruction.

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the vision of **Project Teleportation**, **Smart Capsules**, and **Device Mesh**.

---

## 🤝 Contributing & License

Contributions are welcome! Please check out the issues and PRs.

**License:** MIT License.
