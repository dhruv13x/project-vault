# Strategic Roadmap V3.0

> **Goal:** Balance **Innovation**, **Stability**, and **Debt** to create the ultimate Project Lifecycle Manager.

---

## 🏁 Phase 0: The Core (Stability & Debt)
**Goal**: Solid foundation. Ensure the codebase is robust, tested, and maintainable before scaling features.

- [ ] **Testing**: Increase Code Coverage to > 80% `[Debt]` (Est: L)
    - *Current*: ~65%. *Target*: 80%+. Focus on Sad Path coverage.
- [ ] **CI/CD**: Enforce Linting & Type Checking (Strict `mypy`) `[Debt]` (Est: M)
    - Ensure clean passes for `ruff` and `mypy` across the monorepo.
- [ ] **Refactoring**: Resolve `projectrestore` namespace conflicts `[Debt]` (Est: M)
    - Fix import issues to remove `sys.path` hacks.
- [ ] **Refactoring**: Unify Logging Patterns `[Debt]` (Est: S)
    - Standardize logging across `projectclone`, `projectrestore`, and `src`.
- [ ] **Documentation**: Comprehensive README & Architecture Guide `[Debt]` (Est: M)
    - Update documentation to reflect V3.0 architecture and usage.

---

## 🚀 Phase 1: The Standard (Feature Parity)
**Goal**: Competitiveness. Match and exceed industry standard tooling for backup/restore.
*Requires Phase 0*

- [ ] **Performance**: Parallel Cloud Sync `[Feat]` (Est: M)
    - Implement multi-threaded uploads/downloads (replace sequential loop).
- [ ] **UX**: CLI Error Handling Improvements `[Feat]` (Est: S)
    - Human-readable error messages and actionable suggestions.
- [ ] **Config**: Robust Settings Management `[Feat]` (Est: S)
    - Enhance `pv.toml` handling and environment variable overrides.
- [ ] **Database**: Native Connectors (pg_dump, mysql, sqlite) `[Feat]` (Est: L)
    - First-class support for database dump/restore operations.

---

## 🔌 Phase 2: The Ecosystem (Integration)
**Goal**: Interoperability. Allow Project Vault to connect with other tools and workflows.
*Requires Phase 1*

- [ ] **API**: REST/GraphQL Interface `[Feat]` (Est: L)
    - Expose core engine functionality via a programmable API.
- [ ] **Plugins**: Extension System `[Feat]` (Est: XL)
    - Allow community-contributed plugins for custom backends or hooks.
- [ ] **Integrations**: Git Handshake `[Feat]` (Est: M)
    - Link `pv` snapshots with `git` commits (`pv commit`).

---

## 🔮 Phase 3: The Vision (Innovation)
**Goal**: Market Leader. Pioneer new capabilities in project teleportation.
*Requires Phase 2*

- [ ] **AI**: LLM Integration `[Feat]` (Est: XL)
    - AI-powered `diff` summaries and smart `.pvignore` generation.
- [ ] **Cloud**: Kubernetes & Docker Support `[Feat]` (Est: L)
    - "Container Snapshots": Snapshot running container filesystems.
- [ ] **Security**: Zero-Knowledge Encryption `[Feat]` (Est: M)
    - Client-side encryption before data leaves the machine.
