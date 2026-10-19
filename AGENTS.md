# AGENTS.md — Multi-Agent Working Rules for SecondRoute

> **This file is the contract.** Every agent (human or AI) working in this repository must read this file before starting work and follow it strictly.

---

## 1. Source of Truth

- **PLAN.md** is the authoritative specification. All work must trace to a phase and feature ID (e.g., `F0.3`, `F2.5`).
- **This file (AGENTS.md)** governs how agents coordinate.
- **PROGRESS.md** tracks what is done, in progress, and blocked.
- **All .md files in `docs/`, `backend/`, `frontend/`, `ml/`, `pipelines/`** must be read before touching code in those directories.

---

## 2. Before Any Work

1. **Read all .md files** in the relevant area (PLAN.md, AGENTS.md, PROGRESS.md, and any domain-specific docs).
2. **Check PROGRESS.md** for the current phase, feature ownership, and blockers.
3. **Claim a feature** by adding your agent ID and timestamp to PROGRESS.md under "In Progress".
4. **Do not start** a feature that depends on an incomplete prerequisite (see `Requires` in PLAN.md).

---

## 3. Workflow Rules

| Rule | Description |
|------|-------------|
| **One feature per PR** | Each feature ID (e.g., `F1.3`) gets its own branch and PR. No bundling. |
| **Tests first** | Write failing tests (unit, integration, property) before implementation. Red → Green → Refactor. |
| **CI must pass** | Lint (ruff/eslint), typecheck (mypy), unit tests, and compose smoke test must be green before merge. |
| **No silent failures** | Every error path returns a structured error. No empty catch blocks. |
| **Append-only data** | `decisions`, `outcomes`, `audit_log`, `inspections` are append-only. Never UPDATE or DELETE. |
| **Synthetic flag** | All synthetic data carries `is_synthetic = true`. Never mix synthetic and real in reports without explicit separation. |
| **Source & as-of on every number** | Every price, cost, component value, model metric must have `source` and `as_of` fields. |
| **Licenses checked** | Before adding any library, dataset, or model, verify its license is in Appendix D of PLAN.md and allowed. |
| **No scraping violating ToS** | Only official APIs, public datasets with clear licenses, and partner data under agreement. |

---

## 4. Agent Coordination

### 4.1 Claiming Work
```markdown
## In Progress
- F2.5 — Agent: <agent-id> — Started: 2026-10-20T14:30:00Z — Branch: feat/F2.5-channel-evaluator
```

### 4.2 Completing Work
- Move the feature to "Done" in PROGRESS.md with commit SHA and merge date.
- Update any affected documentation (ADRs, data-sources.md, runbooks).
- Run the full test suite locally before pushing.

### 4.3 Blockers
```markdown
## Blocked
- F3.1 — Blocked on: F2.2 (price source interface not merged) — Since: 2026-10-20
```

### 4.4 Handoffs
- If an agent cannot complete a feature, they must document the current state, remaining tasks, and any decisions made in the PR description and PROGRESS.md.

---

## 5. Code Standards

### Backend (Python)
- **FastAPI + Pydantic v2** for all APIs.
- **SQLAlchemy 2.x + Alembic** for DB.
- **Structured logging** (JSON) via `structlog`.
- **Protocol-based interfaces** (e.g., `PriceSource`) for swappable implementations.
- **Seeded RNG** for all stochastic code (Monte Carlo, synthetic gen).
- **Property tests** with Hypothesis for invariants (monotonicity, determinism).

### Frontend (TypeScript/React)
- **Vite + React 18 + TypeScript + Tailwind + shadcn/ui**.
- **TanStack Query** for server state.
- **React Router** for navigation.
- **IndexedDB (idb)** for offline drafts (Phase 5).
- **Vitest + Playwright** for tests.

### Database
- **PostgreSQL 16** with RLS (Phase 5+).
- **Every table has `org_id`** from Phase 5 onward.
- **Migrations only forward** in main branch; `downgrade` only in feature branches for testing.

---

## 6. Phase Gates (Definition of Done per Phase)

| Phase | Must Be True Before Next Phase |
|-------|--------------------------------|
| 0 | `docker compose up` healthy, CI green, `/health` returns 200, Alembic baseline works |
| 1 | Full intake→inspection→photo flow works in UI, audit log complete, seed data loads idempotently |
| 2 | Decision card renders with synthetic prices, Monte Carlo deterministic, `SAFE_DEFAULT` works, flip conditions shown |
| 3 | Real price adapters replace synthetic, all sources tagged with `source` and `as_of`, decision code unchanged |
| 4 | Override, outcome, regret, calibration computed and visible in analytics, export round-trips |
| 5 | Auth + tenancy enforced (RLS tests pass), offline works, backtest has no look-ahead, staging deploys |
| 6 | Shadow model runs, promotion gate blocks worse models, drift alerts fire, exploration capped |
| 7 | New category added by config only, fraud flags work, partner adapter pattern proven |

---

## 7. Free Resources Only — Hard Constraint

**Every tool, library, dataset, and service MUST be free/open source or have a usable free tier.**

| Category | Approved (from PLAN Appendix A/D) | Forbidden |
|----------|-----------------------------------|-----------|
| LLM API | Ollama (local, open weights) | OpenAI, Anthropic, any paid API as hard dependency |
| Price data | eBay Browse API (free key), FRED, Wikimedia, partner CSV | Keepa, DRAMeXchange, Jungle Scout, paid scrapers |
| ML | scikit-learn, LightGBM, statsmodels, NumPy, MLflow | Databricks, SageMaker, paid managed ML |
| CV | OpenCV, Tesseract, PaddleOCR | Commercial vision APIs |
| Hosting (dev) | Docker Compose, GitHub Actions free tier | Paid cloud without free tier |
| Auth | Keycloak | Auth0, Clerk (unless free tier covers pilot) |

**Before adding ANY dependency:** Check Appendix D of PLAN.md. If not listed, propose an ADR.

---

## 8. Documentation Requirements

| Trigger | Required Doc Update |
|---------|---------------------|
| New architectural decision | ADR in `docs/decisions/` (use template) |
| New data source | Row in `docs/data-sources.md` with license, access, rate limits |
| New migration | Migration file + README update if schema changes |
| New API endpoint | OpenAPI spec auto-generated; add example to README if non-obvious |
| New model version | MLflow entry + `docs/runbooks/` if deployment changes |
| License change | Update `docs/data-sources.md` and ADR |

---

## 9. Testing Requirements

| Layer | Tools | Minimum Coverage |
|-------|-------|------------------|
| Unit (backend) | pytest, Hypothesis | All pure functions, protocols, validators |
| Unit (frontend) | Vitest | All components with logic, hooks, utils |
| Integration | pytest + testcontainers | API endpoints, DB migrations, RLS policies |
| Contract | Schemathesis | OpenAPI spec vs implementation |
| E2E | Playwright | Critical user flows (intake, decision, override) |
| Property | Hypothesis | Monotonicity, determinism, invariants |
| Backtest | Custom | Look-ahead detection (must fail build on leak) |

---

## 10. Security & Privacy

- **No PII in logs** — structured logs must exclude serials, emails, IPs.
- **EXIF stripped** — all uploaded photos have GPS and device info removed (F1.5).
- **RLS enforced** — cross-tenant access returns 403, not 404 (prevents enumeration).
- **Secrets in SOPS** — never commit plaintext secrets.
- **Activation lock flag** — stored, never the actual Apple ID.

---

## 11. Versioning & Releases

- **Semantic versioning** (MAJOR.MINOR.PATCH) tagged on main.
- **Changelog** in `CHANGELOG.md` (Keep a Changelog format).
- **No breaking changes** in a phase without ADR and version bump.

---

## 12. Emergency Procedures

| Situation | Action |
|-----------|--------|
| CI broken on main | All agents stop feature work, fix CI first |
| Data corruption | Follow `docs/runbooks/restore.md` |
| License violation found | Remove dependency immediately, document in ADR |
| Security issue | Private disclosure, patch in branch, release patch version |

---

## 13. Agent ID Format

Use a consistent identifier in PROGRESS.md and commit messages:
- Human: `human-<github-handle>`
- AI: `ai-<model>-<session-suffix>` (e.g., `ai-nemotron-ses_eaa6f421`)

---

## 14. Acknowledgment

By working in this repository, you confirm you have read **PLAN.md**, **AGENTS.md**, and **PROGRESS.md** in full, and will follow these rules.

---

*Last updated: 2026-10-20*
*Version: 1.0*