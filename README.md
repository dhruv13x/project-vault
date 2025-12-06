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
*   **Share:** Send a self-contained `.pvc` capsule to a colleague.
*   **Resurrect:** Restore a dead environment exactly as it was 3 months ago.
*   **Debug:** Snapshot a bug state (including the DB) and analyze it later.

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
*   **`textual`**: For the interactive TUI.
*   **`zstandard`**: For high-performance compression.

### Standalone Tools (Advanced)
For servers, CI/CD, or minimal environments, you can install the components independently:

*   **Backup Only:** `pip install projectclone` (No cloud deps)
*   **Restore Only:** `pip install projectrestore` (Zero dependencies, ultra-lightweight)

---

## ✨ Key Features

*   **Interactive Time Machine**: **(God Level)** Browse, view, and restore files from any snapshot in a terminal-based UI (`pv browse`).
*   **Bit-Identical Verification**: **(God Level)** Verify that a restored project is byte-for-byte identical to the source with `pv verify-clone`.
*   **Capsule Portability**: Export snapshots to single `.pvc` files for sharing via email/USB with `pv capsule export`.
*   **Smart Initialization**: Auto-detects project type (Python, Node, Rust, etc.) and generates optimal ignore patterns with `pv init --smart`.
*   **Cloud Agnostic Sync**: Push/pull encrypted, deduplicated snapshots to AWS S3, Backblaze B2, or any S3-compatible storage.
*   **Content-Addressable Storage**: Every file is stored once, saving space and ensuring data integrity.
*   **Vault Garbage Collection**: Clean up orphaned data blocks from the vault with the `pv gc` command.
*   **Integrity Checks**: Verify the health of your local vault and detect corruption with `pv check-integrity`.
*   **Lifecycle Hooks**: Execute pre/post-backup and pre/post-restore shell commands for seamless integration.
*   **Doppler Secret Integration**: Automatically inject secrets from Doppler for secure cloud access.

---

## ⚡ Quick Start

### 1. Initialize
Run this in your project root. The `--smart` flag auto-detects your language and creates a `.pvignore`.
```bash
pv init --smart
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

### 4. Sync to Cloud (Optional)
Push your encrypted, deduplicated snapshots to S3 or Backblaze B2.
```bash
pv push
```

### 5. Restore (Teleport)
Bring the project back to life on any machine.
```bash
# Restore from a local snapshot
pv vault-restore ./vault/snapshots/my-project/snapshot_latest.json ./restored_project

# Import and restore a portable capsule
pv capsule import my_project.pvc
pv capsule restore ./vault/snapshots/my-project/snapshot_from_capsule.json
```

---

## 🛠️ Commands

| Command | Description |
| :--- | :--- |
| `pv browse` | **(God Level)** Interactive TUI to browse, view, and restore from snapshots. |
| `pv vault` | Create a content-addressable snapshot of the current directory. |
| `pv vault-restore` | Full project restoration from a manifest. |
| `pv capsule export` | Export a snapshot to a portable `.pvc` file. |
| `pv capsule import` | Import a `.pvc` file into the local vault. |
| `pv verify-clone` | **(God Level)** Verify a restored project is bit-identical to the source. |
| `pv status` | Show modified files and cloud sync status. |
| `pv init` | Create configuration. Use `--smart` for auto-ignore generation. |
| `pv push` | Sync local vault to Cloud (S3/B2). |
| `pv pull` | Download missing snapshots from Cloud. |
| `pv list` | List all local or cloud snapshots. |
| `pv diff` | Compare a local file against the latest snapshot. |
| `pv checkout` | Restore a specific file from the latest snapshot. |
| `pv gc` | Run garbage collection to clean up orphaned vault objects. |
| `pv check-integrity`| Verify the health of the local vault (detect corruption). |
| `pv check-env` | Check cloud credentials and dependencies. |
| `pv notify-test` | Send a test notification. |
| `pv config set-creds` | Save credentials to `pv.toml` (requires manual security override). |

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

```toml
[tool.project-vault]
bucket = "my-backup-bucket"
endpoint = "https://s3.us-east-1.amazonaws.com"
vault_path = "./.pv/vault"
```

### Environment Variables & Precedence
`pv` uses a clear hierarchy for resolving settings:

1.  **Command-Line Flags**: `--bucket my-bucket` always wins.
2.  **`PV_` Prefixed Env Vars**: `PV_BUCKET` overrides `BUCKET`.
3.  **Doppler Secrets**: If `DOPPLER_TOKEN` is set, secrets are fetched automatically.
4.  **Standard Env Vars**: `AWS_ACCESS_KEY_ID`, `B2_KEY_ID`, etc.
5.  **Config File**: `pv.toml` or `pyproject.toml`.

> **Security Note**: Use `PV_` prefixed variables or Doppler in CI/CD environments to avoid leaking general-purpose credentials.

### Lifecycle Hooks
Define shell commands in `pv.toml` to run at critical stages.

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
│   └── common/           # Shared utilities (Capsule, Smart Init, etc.)
├── projectclone/         # The Backup Engine
│   └── src/
│       ├── cas_engine.py # Content-Addressable Storage logic
│       ├── verify_engine.py # Bit-identical verification
│       └── gc_engine.py  # Garbage Collection
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
