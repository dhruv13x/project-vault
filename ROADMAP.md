# Strategic Roadmap (V3.0)

> **Vision:** Project Vault creates **100% identical project capsules** – bit-for-bit copies of your live project (code, DBs, caches, configs) that you can restore anywhere.

This roadmap balances **Innovation**, **Stability**, and **Technical Debt**. It uses a phased approach where each phase unlocks the next.

---

## 🏁 Phase 0: The Core (Stability & Debt)
**Goal**: Solid foundation. Ensure the house is built on rock, not sand.

- [x] **Testing**: Maintain Coverage > 80% (Currently ~88%). `[Debt]`
- [ ] **CI/CD**: Enforce strict `mypy` type checking across `src`, `projectclone`, and `projectrestore`. `[Debt]` (Est: M)
- [ ] **Refactoring**: Resolve namespace conflicts in `projectrestore` (remove `sys.path` hacks). `[Debt]` (Est: M)
- [ ] **Standardization**: Unify logging patterns across `projectclone` and `projectrestore`. `[Debt]` (Est: S)
- [ ] **Documentation**: Create a dedicated `DEVELOPER.md` guide for architecture and contribution. `[Docs]` (Est: S)

---

## 🚀 Phase 1: The Standard (Feature Parity)
**Goal**: Competitiveness. Make the tool delightful and robust.
*Requires Phase 0 stability.*

- [ ] **UX**: Enhance `pv browse` TUI with restore/diff actions. `[Feat]` (Est: M)
- [ ] **Config**: Migrate to Pydantic for robust `pv.toml` validation and environment variable overriding. `[Feat]` (Est: S)
- [ ] **Performance**: Implement async/await for S3/B2 cloud operations (replace blocking loops). `[Feat]` (Est: L)
- [ ] **Error Handling**: Standardize error codes and user-facing messages (Rich-formatted). `[Feat]` (Est: M)

---

## 🔌 Phase 2: The Ecosystem (Integration)
**Goal**: Interoperability. Open the vault to the world.
*Requires Phase 1 API design freeze.*

- [ ] **API**: Expose a local REST API (`fastapi`) to interact with the vault programmatically. `[Feat]` (Est: XL)
- [ ] **Plugins**: Create a hook system (pre-backup, post-restore) for database dumps and notifications. `[Feat]` (Est: L)
- [ ] **Integrations**: Native support for Doppler and Infisical for secret management. `[Feat]` (Est: M)

---

## 🔮 Phase 3: The Vision (Innovation)
**Goal**: Market Leader. Features that feel like magic.
*Requires Phase 2 extensibility.*

- [ ] **AI**: LLM-powered `.pvignore` generation (Scan project -> Suggest ignores). `[Feat]` (Est: XL)
- [ ] **AI**: Natural Language Querying ("Show me changes in the login logic since last week"). `[Feat]` (Est: XL)
- [ ] **Cloud**: Kubernetes Operator for scheduled backups of persistent volumes. `[Feat]` (Est: L)
- [ ] **Zero-Knowledge**: Client-side AES-256 encryption before data leaves the machine. `[Feat]` (Est: L)

---

## Legend
- `[Debt]`: Technical Debt / Maintenance
- `[Feat]`: New Feature
- `[Bug]`: Bug Fix
- `[Docs]`: Documentation
- **Est**: T-Shirt Sizing (S/M/L/XL)
