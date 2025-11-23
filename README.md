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

### Standalone Tools (Advanced)
For servers, CI/CD, or minimal environments, you can install the components independently:

*   **Backup Only:** `pip install projectclone` (No cloud deps)
*   **Restore Only:** `pip install projectrestore` (Zero dependencies, ultra-lightweight)

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
| `pv vault` | Create a content-addressable snapshot of the current directory. |
| `pv status` | Show modified files and cloud sync status. |
| `pv diff` | Compare a local file against the latest snapshot. |
| `pv checkout` | Restore a specific file from the latest snapshot. |
| `pv push` | Sync local vault to Cloud (S3/B2). |
| `pv pull` | Download missing snapshots from Cloud. |
| `pv list` | List all local or cloud snapshots. |
| `pv vault-restore` | Full project restoration from a manifest. |
| `pv check-integrity`| Verify the health of the local vault (detect corruption). |

---

## 🧩 Architecture

Project Vault is a **monorepo** containing three distinct tools:

1.  **`project-vault` (pv):** The orchestrator. Handles configuration, cloud sync, and user interaction.
2.  **`projectclone`:** The backup engine. Handles hashing, deduplication, and manifest generation.
3.  **`projectrestore`:** The restore engine. A standalone, dependency-free tool focused purely on safe data reconstruction.

---

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the vision of **Project Teleportation**, **Smart Capsules**, and **Device Mesh**.

---

## 📄 License

MIT License.