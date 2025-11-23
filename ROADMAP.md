# Project Vault Roadmap

> **Core Vision:**  
> Project Vault creates **100% identical project capsules** – bit-for-bit copies of your live project
> (code, DBs, caches, configs, env files, everything) that you can restore on any machine and keep
> working as if nothing changed. If you compare original vs restored with `diff -r`, you should see **nothing**.

This roadmap is organized by **levels of power** rather than only versions:

- **Level 0 — Foundation (Now)**
- **Level 1 — Smart Capsules (Current Focus)**
- **Level 2 — Time & Navigation**
- **Level 3 — UX, Ecosystem & Integrations**
- **Level 4 — Security & Trust**
- **Level 5 — GOD Level (Project Reality Bending)**

Each level deepens the same core superpower:  
**“Teleport my entire project state anywhere, safely and predictably.”**

---

## Level 0 — Foundation (Completed)

These are the core building blocks already implemented.

### Core Engine & CLI

- [x] **Core CAS Engine:** Content-Addressable Storage for deduplication.
- [x] `backup` – Create backups (full, incremental, archive)
- [x] `archive-restore` – Safely restore archive backups
- [x] `vault` – Content-addressable backup into vault (objects + manifests)
- [x] `vault-restore` – Restore project from a vault manifest
- [x] `init` – Initialize configuration / `pv.toml` / defaults
- [x] `gc` – Garbage collect orphaned objects
- [x] `check-integrity` – Verify local vault health (missing/corrupt objects)

### Cloud & Sync

- [x] `push` – Push vault to cloud storage (S3/B2), with `--dry-run`.
- [x] `pull` – Download missing backups from cloud, with `--dry-run`.
- [x] `check-env` – Verify cloud environment variables (S3/B2).

### Workspace Insight & Local State

- [x] `status` – Show workspace + vault status (what changed vs latest snapshot).
- [x] `diff` – Compare local file vs latest snapshot (`pv diff <file>`).
- [x] `checkout` – Restore single file from latest snapshot (`pv checkout <file>`).
- [x] `list` – List available snapshots locally or in cloud.

### Project Teleportation (Killer Feature)

- [x] **Perfect clone of current project state**:
  - Captures **everything** in the project (code, env files, caches, databases, assets).
  - "Zero-Trust" restoration (no absolute paths/traversal).

---

## Level 1 — Smart Capsules (Current Focus)

Goal: Enhance usability, intelligence, and verifiable correctness. Make `pv` smarter about *what* it stores and *how*.

### 1.1. Metadata Indexing (Completed/In-Progress)

- [x] **Store Metadata:** Capture file permissions (chmod) and timestamps (mtime) in manifest (V2 Format).
- [x] **Restore Metadata:** Apply permissions and timestamps correctly on restore/checkout.
- [ ] **Symlink Support:** Store symlinks as first-class objects (not just following them).

### 1.2. Smart Configuration

- [ ] **Auto-Configuration (`pv init --smart`):**
    - Auto-detect project type (Python, Node, Rust).
    - Generate optimized `.vaultignore` (e.g., ignore `node_modules` but keep `.env`).
- [ ] **Ignore/Include Rules:**
    - `.pvignore` support (distinct from `.gitignore` for snapshot payloads).

### 1.3. Verify-Clone (Prove the Magic)

- [ ] `pv verify-clone <original_path> <clone_path>`:
  - Walk both trees and verify bit-identical content.
  - Show friendly summary: `Verification successful: Capsule is perfect.`

### 1.4. First-class "Capsule" Concept

- [ ] Introduce `pv capsule create` / `restore` aliases.
- [ ] Official on-disk capsule format (`*.pvc`) for sharing.
- [ ] Capsule Metadata: Embed `source_os`, `hostname`, `created_at` in snapshots.

---

## Level 2 — Time & Navigation (Project Time Machine)

Goal: Extend teleportation in **time**, not just space.

### 2.1. Snapshot Timeline

- [ ] `pv history`: Chronological list with filtering (`--host`, `--since`).
- [ ] **Interactive TUI:** Browse snapshots and view diffs visually (`pv interactive`).

### 2.2. Snapshot Diffs & Restore

- [ ] `pv diff --snapshot A --snapshot B`: Compare state between two points in time.
- [ ] `pv restore --snapshot <id>`: Full project restore to specific state.
- [ ] `pv checkout <file> --snapshot <id>`: Surgical restore from history.

### 2.3. Labels & Bookmarks

- [ ] `pv tag add <name>`: Label important states (e.g., "stable-v1").

---

## Level 3 — UX, Ecosystem & Integrations

Goal: Make Project Vault feel like a natural part of daily dev life.

### 3.1. Performance Optimization

- [ ] **Parallel Cloud Sync:** Multi-threaded uploads/downloads.
- [ ] **Fast Hashing:** Use xxHash for local disk operations (faster than SHA256).
- [ ] **Compression:** Zstandard (zstd) compression for objects.

### 3.2. Golden Workflows

- [ ] Document recipes: "New Machine Migration", "Bug Capsules", "Cloud Resurrection".
- [ ] Configurable defaults in `pv.toml`.

---

## Level 4 — Security & Trust

Goal: Make sure that what you store and ship is safe.

### 4.1. Client-side Encryption

- [ ] **Zero-Knowledge Encryption:** AES-256-GCM encryption of objects *before* they hit the disk/cloud.
- [ ] Key management (Passphrase or Keyfile).

### 4.2. Redacted Capsules

- [ ] `pv capsule create --redacted`: Automatically exclude secrets (`.env`) based on policy.

### 4.3. Enhanced Integrity

- [ ] Hash chains or manifest signatures.
- [ ] `pv check-integrity --deep`: Verify entire history.

---

## Level 5 — GOD Level (Reality-Bending Project Control)

Goal: Your project becomes a portable, continuous, self-healing entity.

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
- [ ] **Data Provenance:** Track which snapshot generated which output file.

---

## Guiding Principles

1. **Never lie about state.** If something can’t be restored, say so.
2. **Project-centric, not file-centric.** Think in terms of the "living project."
3. **Boringly reliable.** Teleportation must be rock solid.
4. **Embrace “dirty reality”.** Handle the mess that Git ignores.