# Project Vault Roadmap

> **Core Vision:**  
> Project Vault creates **100% identical project capsules** – bit-for-bit copies of your live project
> (code, DBs, caches, configs, env files, everything) that you can restore on any machine and keep
> working as if nothing changed. If you compare original vs restored with `diff -r`, you should see **nothing**.

This roadmap is organized by **levels of power** rather than only versions:

- **Phase 1: Foundation (CRITICALLY MUST HAVE)**
- **Phase 2: The Standard (MUST HAVE)**
- **Phase 3: The Ecosystem (INTEGRATION & SHOULD HAVE)**
- **Phase 4: The Vision (GOD LEVEL)**
- **The Sandbox (OUT OF THE BOX / OPTIONAL)**

Each level deepens the same core superpower:  
**“Teleport my entire project state anywhere, safely and predictably.”**

---

## Phase 1: Foundation (Q1)

**Focus**: Core functionality, stability, security, and basic usage.

### Core Engine & CLI

- [x] **Core CAS Engine:** Content-Addressable Storage for deduplication.
- [x] `backup` – Create backups (full, incremental, archive).
- [x] `archive-restore` – Safely restore archive backups.
- [x] `vault` – Content-addressable backup into vault (objects + manifests).
- [x] `vault-restore` – Restore project from a vault manifest.
- [x] `init` – Initialize configuration / `pv.toml` / defaults.
- [x] `gc` – Garbage collect orphaned objects.
- [x] `check-integrity` – Verify local vault health (missing/corrupt objects).

### Cloud & Sync

- [x] `push` – Push vault to cloud storage (S3/B2), with `--dry-run`.
- [x] `pull` – Download missing backups from cloud, with `--dry-run`.
- [x] `check-env` – Verify cloud environment variables (S3/B2).

### Workspace Insight & Local State

- [x] `status` – Show workspace + vault status (what changed vs latest snapshot).
- [x] `diff` – Compare local file vs latest snapshot (`pv diff <file>`).
- [x] `checkout` – Restore single file from latest snapshot (`pv checkout <file>`).
- [x] `list` – List available snapshots locally or in cloud.

---

## Phase 2: The Standard (Q2)

**Focus**: Feature parity with top competitors, user experience improvements, and robust error handling.

### 2.1. Metadata Indexing

- [x] **Store Metadata:** Capture file permissions (chmod) and timestamps (mtime) in manifest (V2 Format).
- [x] **Restore Metadata:** Apply permissions and timestamps correctly on restore/checkout.
- [x] **Symlink Support:** Store symlinks as first-class objects (not just following them).

### 2.2. Smart Configuration

- [ ] **Auto-Configuration (`pv init --smart`):**
    - [ ] Integrate `smart_init.py` logic into CLI.
    - [x] Logic to detect project type (Python, Node, Rust).
    - [x] Logic to generate optimized `.pvignore` (ignore `node_modules` but keep `.env`).
- [ ] **Ignore/Include Rules:**
    - [ ] Full `.pvignore` support (distinct from `.gitignore` for snapshot payloads).

### 2.3. Verify-Clone (Prove the Magic)

- [ ] `pv verify-clone <original_path> <clone_path>`:
  - Walk both trees and verify bit-identical content.
  - Show friendly summary: `Verification successful: Capsule is perfect.`

### 2.4. First-class "Capsule" Concept

- [ ] Introduce `pv capsule create` / `restore` aliases.
- [ ] Official on-disk capsule format (`*.pvc`) for sharing via USB/Email.
- [ ] Capsule Metadata: Embed `source_os`, `hostname`, `created_at` in snapshots.

---

## Phase 3: The Ecosystem (Q3)

**Focus**: Webhooks, API exposure, 3rd party plugins, SDK generation, and extensibility.

### 3.1. Performance Optimization

- [ ] **Parallel Cloud Sync:** Multi-threaded uploads/downloads (replace sequential loop in `sync_engine.py`).
- [ ] **Fast Hashing:** Use xxHash for local disk operations (faster than SHA256).
- [x] **Compression:** Zstandard (zstd) compression for objects.

### 3.2. Integrations

- [x] **Doppler Support:**
    - Automatically fetch cloud credentials (AWS/B2 keys) and other configurations from a detected Doppler environment.
- [ ] **Infisical Support:**
    - Add support for Infisical as a secret provider.
- [ ] **Database Connectors:**
    - Native hooks for `pg_dump`, `mysqldump`, `sqlite3` backup.
    - `pv db dump` / `pv db restore`.
- [ ] **Git Handshake:**
    - `pv commit`: Create a Git commit and a PV snapshot simultaneously, linking the two.

---

## Phase 4: The Vision (Q4)

**Focus**: "Futuristic" features, AI integration, advanced automation, and industry-disrupting capabilities.

### 4.1. Snapshot Timeline

- [ ] `pv history`: Chronological list with filtering (`--host`, `--since`).
- [x] **Interactive TUI:** Browse snapshots and view diffs visually (`pv browse`).

### 4.2. Snapshot Diffs & Restore

- [ ] `pv diff --snapshot A --snapshot B`: Compare state between two points in time.
- [ ] `pv restore --snapshot <id>`: Full project restore to specific state.
- [ ] `pv checkout <file> --snapshot <id>`: Surgical restore from history.

### 4.3. Security & Compliance

- [ ] **Zero-Knowledge Encryption:** AES-256-GCM encryption of objects *before* they hit the disk/cloud.
- [ ] **Redacted Capsules:** `pv capsule create --redacted` to automatically exclude secrets (`.env`) based on policy.
- [ ] **Data Provenance:** Cryptographically sign snapshots to prove origin and integrity.

### 4.4. Container Integration

- [ ] **Container Snapshots:** `pv vault --container <id>` to snapshot a running container's filesystem.

---

## The Sandbox (Beyond Q4)

**Focus**: Wild, creative, experimental ideas that set the project apart.

### 5.1. Cross-OS Rebinding

- [ ] **Environment Rebinding (Plugins):**
    - Detect OS differences on restore.
    - **Path Rewriting:** Fix absolute paths in configs.
    - **Runtime Sanitization:** Auto-reinstall dependencies (e.g., `npm install`) when moving OS.

### 5.2. Continuous Capsules

- [ ] `pv daemon`: Background auto-snapshots based on time or file changes.
- [ ] Smart pruning (keep dense recent history, sparse older history).

### 5.3. Device Mesh

- [ ] Named devices (`laptop`, `phone`).
- [ ] `pv push --from laptop` / `pv pull --to desktop`.

### 5.4. Research & AI Integration

- [ ] **Large File Support (LFS):** Chunking for multi-GB model weights.
- [ ] **AI-powered `.vaultignore`:**
    - Train a model to predict which files should be ignored based on the project type.
- [ ] **AI-powered `diff`:**
    - Use AI to summarize the changes between two snapshots in natural language.
