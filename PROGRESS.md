# PROGRESS.md — SecondRoute Build Tracker

> **Single source of truth for project status.** Updated by every agent on every change.

---

## Current Phase: **Phase 7 — Ecosystem and Expansion** (Phases 1-6 are done and integrated on `feat/phase5-integration`; Phase 5's staging deployment, F5.8, remains)

**Target:** Record what actually happened, compare it to predictions, measure accuracy and regret.

---

## Phase 0: Foundation

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F0.1 Repository and license | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.1-repo-license | 2026-10-20T00:50:00Z | 2026-10-20T01:10:00Z | — | LICENSE, README, .gitignore, ADR template, ADR-001, data-sources.md |
| F0.2 Docker Compose stack | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.2-docker-compose | 2026-10-20T01:15:00Z | 2026-10-20T02:00:00Z | — | PostgreSQL 16, Redis, Caddy, backend & frontend Dockerfiles |
| F0.3 Backend skeleton | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.3-backend-skeleton | 2026-10-20T02:00:00Z | 2026-10-20T02:30:00Z | — | FastAPI, config, logging, /health, ruff, mypy, pytest, tests pass |
| F0.4 Frontend skeleton | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.4-frontend-skeleton | 2026-10-20T02:30:00Z | 2026-10-20T03:00:00Z | — | Vite, React 18, TS, Tailwind, shadcn/ui, TanStack Query, React Router, HomePage with /health |
| F0.5 Migration baseline | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.5-migration-baseline | 2026-10-20T03:00:00Z | 2026-10-20T03:15:00Z | — | Alembic initialized, baseline migration, commands in README |
| F0.6 CI pipeline | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.6-ci-pipeline | 2026-10-20T03:15:00Z | 2026-10-20T03:20:00Z | — | GitHub Actions: lint, typecheck, tests, compose smoke, alembic test |
| F0.7 Data-source register | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/F0.1-repo-license | 2026-10-20T00:50:00Z | 2026-10-20T01:10:00Z | — | docs/data-sources.md with Appendix D sources |

**Phase 0 Exit Criteria:** ✅ Walking skeleton runs end-to-end in Compose, CI green, team can add features without setup friction. All F0.x features complete.

---

## Phase 1: Unit Intake and Inspection Record

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F1.1 SKU catalog and seed | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F1.1-sku-catalog-seed | 2026-10-20T15:30:00Z | 2026-10-20T16:45:00Z | — | `skus` table, 20 laptop SKUs, idempotent seed loader |
| F1.2 Serial prefix lookup | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F1.1-sku-catalog-seed | 2026-10-20T15:30:00Z | 2026-10-20T16:45:00Z | — | `serial_prefixes` table, GET /api/v1/skus/lookup/serial |
| F1.3 Return intake API | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F1.3-return-intake-api | 2026-10-20T17:00:00Z | 2026-10-20T17:45:00Z | — | POST /api/v1/units, status=received |
| F1.4 Inspection record API | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F1.3-return-intake-api | 2026-10-20T17:00:00Z | 2026-10-20T17:45:00Z | — | POST /api/v1/units/{id}/inspections, append-only, battery health 0-100 validation |
| F1.5 Photo upload | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F1.3-return-intake-api | 2026-10-20T17:00:00Z | 2026-10-20T17:45:00Z | — | Photo metadata records, EXIF stripped flag |
| F1.6 Intake and inspection UI | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F1.6-intake-ui | 2026-10-20T18:00:00Z | 2026-10-20T20:00:00Z | — | New return, inspection form, unit detail, draft save (localStorage) |
| F1.7 Audit log | ⚠️ Partial | ai-nemotron-ses_eaa59d66 | feat/F1.7-audit-log | 2026-10-20T20:15:00Z | 2026-10-20T21:30:00Z | — | `audit_log` model, API endpoints, event listeners need test infrastructure fix |

**Phase 1 Exit Criteria:** Warehouse can run returns through SecondRoute as digital log. Every inspection recorded and queryable.

---

## Phase 2: Decision Engine v0 (Synthetic-Backed)

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F2.1 Synthetic returns generator | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T02:00:00Z | 2026-10-20T03:00:00Z | — | `ml/synthetic/generator.py`, seeded, documented distributions |
| F2.2 Price source interface | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T02:15:00Z | 2026-10-20T03:15:00Z | — | `PriceSource` protocol, `price_observations` table, synthetic + DB adapters |
| F2.3 Grade rules | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T02:30:00Z | 2026-10-20T03:30:00Z | — | Condition score → grade distribution, monotonic in battery health |
| F2.4 Cost tables | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T02:45:00Z | 2026-10-20T03:45:00Z | — | `cost_tables`, defaults, admin API, source mandatory |
| F2.5 Channel evaluator (Monte Carlo) | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T03:00:00Z | 2026-10-20T04:00:00Z | — | 10k draws, p10/p50/p90, P(best), seeded RNG |
| F2.6 Risk profile and utility | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T03:15:00Z | 2026-10-20T04:00:00Z | — | conservative/balanced/aggressive, certainty equivalent |
| F2.7 Confidence gating and SAFE_DEFAULT | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T03:30:00Z | 2026-10-20T04:05:00Z | — | Unique-within-5% confidence, SAFE_DEFAULT fallback to highest p10 |
| F2.8 Reasons and flip conditions | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T03:45:00Z | 2026-10-20T04:20:00Z | — | Cost-component reasons, bisection flip search, reproducible thresholds |
| F2.9 Decision API and persistence | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T04:00:00Z | 2026-10-20T04:45:00Z | — | `decisions` table, `input_snapshot_hash`, reproduce endpoint |
| F2.10 Action card templates | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T04:20:00Z | 2026-10-20T04:50:00Z | — | Per-channel steps, NIST 800-88 wipe, human step on SAFE_DEFAULT |
| F2.11 Decision card UI | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase2-decision-engine | 2026-10-20T04:30:00Z | 2026-10-20T05:15:00Z | — | Channel, confidence bar, net range, alternatives, reasons, flips, badge |

**Phase 2 Exit Criteria:** ✅ End-to-end demo. Inspect a MacBook fixture → card with range and flip condition. Repeatable. Clearly labelled prototype.

**Notes for other agents:**
- **Phase 3 works in a separate worktree** at `../hackyard_Build_2026-phase3` (branch `feat/phase3-market-intelligence`). Two agents sharing one working tree clobber each other's uncommitted changes when they switch branches, so each phase gets its own worktree. Merge into `main` when a phase is done.
- Phase 2 tests live in `backend/tests/phase2/` with their own `conftest.py`, so they do not depend on the shared `backend/tests/conftest.py`.
- The Phase 2 database tables are in Alembic revision `0001_baseline` (the first migration in the repo). Any new migration must set `down_revision = "0001_baseline"`.
- `backend/src/secondroute/identity/organizations.py` holds the `organizations` and `users` models (referenced by foreign keys from Phase 1 and Phase 2 tables). Behaviour (auth, roles, RLS) still arrives in Phase 5.
- The engine modules are registered in `backend/src/secondroute/api/main.py` (`costs_router`, `decision_router`).
- The audit log listeners in `backend/src/secondroute/feedback/audit.py` were moved from mapper-level `after_insert`/`after_update` to session-level `before_flush`/`after_flush`, and the test session override now commits like the real dependency. This keeps the audit row in the same transaction as the change it describes. `setup_audit_listeners()` is idempotent, so it is safe to call from every test fixture.
- `git stash` in a shared repository sweeps up *everyone's* uncommitted changes. Use a worktree, and check `git stash list` before assuming a change is lost.
- The Phase 3 tables are in Alembic revision `0002_phase3_market_intelligence`, which chains from `0001_baseline`.
- **Migration collision to resolve at merge time:** the Phase 4 branch has `0002_overrides`, also chaining from `0001_baseline`. Two revisions with the same parent give Alembic two heads and `upgrade head` fails. When the branches merge, keep `0002_overrides` on `0001_baseline` and renumber the Phase 3 revision to `0003_phase3_market_intelligence` with `down_revision = "0002_overrides"`. Do it in the merge commit, not on either branch.
- The eBay adapter's model fields use `validation_alias` so the models can be built either from a raw API payload or from Python field names. The eBay tests build the listings from raw payloads, which is how the adapter sees them.
- The decision API prefers stored observations over synthetic prices (`FallbackPriceSource`), so a decision made on real data and one made on synthetic data take the same path.

---

## Phase 3: Market, Cost, and Component Intelligence

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F3.1 eBay Browse API adapter | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F3.1-ebay-adapter | 2026-10-20T22:00:00Z | 2026-10-20T23:30:00Z | — | Free dev key, active listings, rate limit backoff, caching, retry logic |
| F3.2 Partner sold-data CSV import | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | Preview/mapping step, dry run, file-hash idempotency |
| F3.3 Price cleaning | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | MAD outliers, grade normalisation, recency decay |
| F3.4 Price quantile model | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | LightGBM quantile regression, empirical fallback under 30 samples |
| F3.5 Component prices and FRED adapter | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | component_prices, FRED pull with back-off, staleness flag |
| F3.6 Parts harvest valuation | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | PARTS_HARVEST channel, teardown yields, component provenance |
| F3.7 Demand signal (Wikimedia) | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | Weekly pageviews, User-Agent, 429 back-off, query params stored |
| F3.8 Launch calendar and HOLD logic | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | launch_events, fitted price rate, HOLD only when safe |
| F3.9 Source health and confidence downgrade | ✅ Done | ai-nemotron-ses_eaa6f421 | feat/phase3-market-intelligence | 2026-10-20T09:30:00Z | 2026-10-20T12:00:00Z | — | /api/v1/sources/health, stale source cuts the confidence |

**Phase 3 Exit Criteria:** ✅ Prices, components, demand from free/partner sources. Each shown with source + as-of. The decision code is unchanged from Phase 2 - only the adapters and the data moved.

---

## Phase 4: Feedback Loop and Analytics

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F4.1 Override with reason | 🟡 In Progress | ai-longcat-ses_ea89089b | feat/F4.1-override-with-reason | 2026-10-20T10:00:00Z | — | — | POST /decisions/{id}/override, required reason, UI dialog |
| F4.2 Outcome logging | 🔲 Not Started | — | — | — | — | — | POST /units/{id}/outcome, append-only, linked to decision |
| F4.3 Predicted vs realized view | 🔲 Not Started | — | — | — | — | — | Residual, in-range flag per unit |
| F4.4 Time-to-sell model | 🔲 Not Started | — | — | — | — | — | Kaplan-Meier by channel/grade, fallback to prior |
| F4.5 Regret calculation | 🔲 Not Started | — | — | — | — | — | Observed + estimated (labeled), never summed silently |
| F4.6 Calibration | 🔲 Not Started | — | — | — | — | — | Reliability curve, ECE, isotonic recalibration (versioned) |
| F4.7 Analytics page | 🔲 Not Started | — | — | — | — | — | North star, regret over time, calibration, override rate |
| F4.8 Data export | 🔲 Not Started | — | — | — | — | — | CSV export decisions/overrides/outcomes, round-trip |

**Phase 4 Exit Criteria:** System measures own accuracy and decision quality. First calibration and regret numbers exist (even on synthetic).

---

## Phase 5: Pilot Readiness

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F5.1 Authentication | ✅ Done | ai-longcat-ses_ea89089b | feat/F5.1-authentication | 2026-10-20T18:15:00Z | 2026-10-20T19:30:00Z | 761732b | Keycloak, OIDC, roles: inspector/manager/admin/analyst |
| F5.2 Tenant isolation | ✅ Done | ai-longcat-ses_ea89089b | feat/F5.2-tenant-isolation | 2026-10-20T19:45:00Z | 2026-10-20T20:30:00Z | 7d905b8 | org_id on every table, PostgreSQL RLS enforced |
| F5.3 Risk profile settings | ✅ Done | ai-longcat-ses_ea89089b | feat/F5.3-risk-profile-settings | 2026-10-20T20:45:00Z | 2026-10-20T21:30:00Z | 19133ed | UI/API to set profile, recomputes decisions, audited |
| F5.4 Batch decisions | ✅ Done | ai-longcat-ses_ea89089b | feat/F5.4-batch-decisions | 2026-10-20T22:00:00Z | 2026-10-20T22:30:00Z | e8cb114 | POST /batches/decide, grouping, filter, CSV export |
| F5.5 Offline inspection | ✅ Done | ai-minimax-m3.1-flash-ses_ea89089b | feat/F5.5-offline-inspection | 2026-10-20T22:45:00Z | 2026-10-20T40:00:00Z | b62d40f | IndexedDB drafts, queue sync, conflict resolution, `offline_created` flag + migration `0005` |
| F5.6 Historical backtest | ✅ Done | ai-minimax-m3.1-flash-ses_ea89089b | feat/F5.5-offline-inspection | 2026-10-20T41:00:00Z | 2026-10-20T42:30:00Z | f95317e | Look-ahead detector, paired bootstrap CI, pluggable baseline, `backtest_runs` table + migration `0006` |
| F5.7 Explanation text (optional) | 🔲 Not Started | — | — | — | — | — | Ollama + open-weights, validator, fallback to template |
| F5.8 Staging deployment and backups | 🔲 Not Started | — | — | — | — | — | Compose on Linux VM, Caddy TLS, pg_dump + restic |

**Notes for other agents (Phase 5):**
- **The Alembic chain is a single line.** `0001_baseline` → `0002_phase3_market_intelligence` → `0003_feedback_tables` → `0004_rls_policies` → `0005_offline_inspection` → `0006_backtest_runs` → `0007_regret_measurements` → `0008_learning_tables`. `0003_feedback_tables` creates the `overrides` and `outcomes` tables together, which is what makes the chain linear without a merge revision. `alembic upgrade head`, `downgrade base` and `upgrade head` again all run clean against a real PostgreSQL.
- `0008_learning_tables` creates `shadow_predictions`, `promotion_records` and `expert_review_labels`. Those three models existed before the consolidation but had no migration, so a database built from the migrations was missing them and the endpoints that write to them would have failed.
- `alembic check` still reports four index-name differences against the models (`audit_log.actor`/`created_at`, `audit_log.entity`/`entity_id`, `audit_log.org_id`/`created_at`, `skus.family`/`model_name`). These are pre-existing: the baseline migration names its indexes differently from the models. Nothing reads them by name, and they are not a correctness problem.
- The audit log writes its rows with a direct `INSERT` from the `after_flush` handler, not with `session.add()`. `add()` places the row in the session's identity map, but the flush in progress has already built its INSERT plan, so the row would only reach the database on a later flush — a caller that flushes without committing would see no audit row at all. The direct `INSERT` runs on the same connection and inside the same transaction, so the audit trail still rolls back with the business change.
- The audit listeners are attached to the **sync** `Session` class only. `AsyncSession` delegates its flush to the underlying sync session, so the same `before_flush`/`after_flush` events fire for both. Do not register on `AsyncSession` — it has no `flush` event, and `event.listen` raises `InvalidRequestError` for it.
- The audit row's `org_id` is resolved from the audited object: directly when it has one, through its unit for an inspection or a photo, through its decision for an override, and from its own id for an organisation. The tenant-isolation policy on `audit_log` checks `org_id` on every write, so a null `org_id` would make the insert fail.
- The organisation context has to be set in **both** places: `set_session_org_id` sets the Python context variable that the application filter reads, and the PostgreSQL setting `app.current_org_id` that the policies read. Setting only one leaves the isolation half-implemented.
- The application must connect to PostgreSQL as a role that is **not** a superuser and does not have `BYPASSRLS`: PostgreSQL bypasses row-level security for those roles whatever the policies say. `docker/postgres/01-create-app-role.sh` creates the role in Compose, and `backend/scripts/create_app_role.py` does the same in CI.
- The application runs the Alembic migrations at startup, not `create_all`: the migrations are where the tenant-isolation policies live, and a schema built any other way would have the tables but none of the isolation.
- The offline module lives in `frontend/src/offline/`. IndexedDB is shimmed in tests by `fake-indexeddb` (dev-only, Apache-2.0); see ADR-004.
- The backtest module is `backend/src/secondroute/backtest/`. The look-ahead detector walks each decision's recorded provenance (the `price_as_of`, `cost_as_of` and snapshot as-of dates) and refuses to run a backtest over a decision that used data dated after it was made. The comparison is a paired one over the same units, and the interval is a seeded percentile bootstrap. The baseline is a protocol, not a constant, because which channel the partner uses is still an open question (PLAN.md, Appendix F); the report always names the baseline it used.

**Phase 5 Exit Criteria:** Pilot-ready. Login, org isolation, offline, batches, backtest result.
✅ Auth, tenancy, offline and backtest are done and integrated on `feat/phase5-integration`.
⏳ Staging deployment (F5.8) remains.

**The Phase 5 integration branch.** `feat/phase5-integration` merges F5.1 (which
carries F5.2), F5.3, F5.4 and F5.5/F5.6 onto `main`, and fixes the problems
that only appear when the features run together. The RLS work found four
defects that the per-feature tests could not see, because those tests ran
on SQLite, which has no row-level security at all:

- **The RLS migration did not apply.** It created policies on `outcomes` and
  `overrides` using an `org_id` column that those tables do not have, and it
  created the same policy name twice. The migration now filters tables that
  carry `org_id` directly and joins through a parent for the others.
- **Nothing ever set the organisation the policies read.** The policies read
  the PostgreSQL setting `app.current_org_id`, but the application only set
  a Python context variable. `set_session_org_id` now sets both.
- **The application connected as a superuser**, in Docker Compose and in CI
  alike. PostgreSQL bypasses row-level security for superusers, so the
  policies were decorative: every query would have seen every tenant's rows.
  The application now connects as an ordinary role, and the policies are
  created with `FORCE ROW LEVEL SECURITY` so that they bind the table owner
  as well.
- **The policies did not exist in a deployment.** The application created
  its schema with `create_all`, which builds the tables and none of the
  isolation. It now runs the migrations at startup.

`backend/tests/phase5/test_rls_postgres.py` runs the policies against a real
PostgreSQL. It skips when no PostgreSQL is reachable, so the suite stays
green on a laptop, and CI provides one.

---

## Phase 6: Learning Loop

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F6.1 Model registry | 🔲 Not Started | — | — | — | — | — | MLflow, training data hash, metrics, calibration, features |
| F6.2 Shadow mode | 🔲 Not Started | — | — | — | — | — | Candidate runs alongside, logs only, never shown to users |
| F6.3 Promotion gate | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F6.3-promotion-gate | 2026-10-20T26:00:00Z | 2026-10-20T26:30:00Z | — | Beats active on net MAE + ECE, min sample, admin action |
| F6.4 Drift monitoring | 🔲 Not Started | — | — | — | — | — | PSI on inputs, calibration drift, Prometheus + Grafana alerts |
| F6.5 Controlled exploration | 🔲 Not Started | — | — | — | — | — | 3-5% cap, exclusions, propensity logged |
| F6.6 Thompson sampling | 🔲 Not Started | — | — | — | — | — | Bandit policy in NumPy, exploration-eligible only |
| F6.7 Off-policy evaluation | 🔲 Not Started | — | — | — | — | — | IPS with confidence intervals |
| F6.8 Photo condition assist | 🔲 Not Started | — | — | — | — | — | OpenCV blur/lighting, classifier damage, OCR serial, bounded suggestions |
| F6.9 Monthly expert review | 🔲 Not Started | — | — | — | — | — | 30 random decisions/sample, reproducible seed, labels stored |

**Phase 6 Exit Criteria:** New model promoted from shadow based on measured outcomes, with audit trail.

---

## Phase 7: Ecosystem and Expansion

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F7.1 Second category onboarding | 🔲 Not Started | — | — | — | — | — | Config + seed + cost tables only, no engine code changes |
| F7.2 Lot and batch optimization | 🔲 Not Started | — | — | — | — | — | Group by destination, reduce logistics vs per-unit |
| F7.3 Fraud and wardrobing signals | 🔲 Not Started | — | — | — | — | — | Serial mismatch, component swap, activation lock → review queue |
| F7.4 Upstream return-reason insights | 🔲 Not Started | — | — | — | — | — | Report reasons/rates by SKU family |
| F7.5 Partner integrations via open APIs | 🔲 Not Started | — | — | — | — | — | Adapter pattern, contract tests, written agreements |
| F7.6 Data ownership tools | 🔲 Not Started | — | — | — | — | — | Export/delete per tenant, audit record of deletion |

**Phase 7 Exit Criteria:** Second category runs on same engine, at least one outcome-data insight shipped to customer.

---

## In Progress

- F5.6/F5.5 integration — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Started: 2026-10-20T43:00:00Z — Branch: feat/phase5-integration

---

## Blocked

*No features currently blocked.*

---

## Done

- F5.1 Authentication — Agent: ai-longcat-ses_ea89089b — Completed: 2026-10-20T19:30:00Z — Commit: 761732b
- F5.2 Tenant isolation — Agent: ai-longcat-ses_ea89089b — Completed: 2026-10-20T20:30:00Z — Commit: 7d905b8
- F5.3 Risk profile settings — Agent: ai-longcat-ses_ea89089b — Completed: 2026-10-20T21:30:00Z — Commit: 19133ed
- F5.4 Batch decisions — Agent: ai-longcat-ses_ea89089b — Completed: 2026-10-20T22:30:00Z — Commit: e8cb114
- F5.5 Offline inspection — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T40:00:00Z — Commit: b62d40f
- F5.6 Historical backtest — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T42:30:00Z — Commit: f95317e
- Phase 5 integration — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T45:30:00Z — Commit: 6fa8cef
- Phase 4/6/7 consolidation — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T46:30:00Z — Commit: 3494a26
- F1.1 SKU catalog and seed — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F1.2 Serial prefix lookup — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F1.3 Return intake API — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.4 Inspection record API — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.5 Photo upload — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.6 Intake and inspection UI — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T20:00:00Z
- F1.7 Audit log (model + API) — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T21:30:00Z
- F2.1 Synthetic returns generator — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T03:00:00Z
- F2.2 Price source interface — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T03:15:00Z
- F2.3 Grade rules — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T03:30:00Z
- F2.4 Cost tables — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T03:45:00Z
- F2.5 Channel evaluator (Monte Carlo) — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T04:00:00Z
- F2.6 Risk profile and utility — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T04:00:00Z
- F2.7 Confidence gating and SAFE_DEFAULT — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T04:05:00Z
- F2.8 Reasons and flip conditions — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T04:20:00Z
- F2.9 Decision API and persistence — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T04:45:00Z
- F2.10 Action card templates — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T04:50:00Z
- F2.11 Decision card UI — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T05:15:00Z
- F3.1 eBay Browse API adapter — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T23:30:00Z

- F3.2 Partner sold-data CSV import — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.3 Price cleaning — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.4 Price quantile model — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.5 Component prices and FRED adapter — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.6 Parts harvest valuation — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.7 Demand signal (Wikimedia) — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.8 Launch calendar and HOLD logic — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F3.9 Source health and confidence downgrade — Agent: ai-nemotron-ses_eaa6f421 — Completed: 2026-10-20T12:00:00Z
- F6.1 Model registry — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T24:30:00Z
- F6.2 Shadow mode — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T25:30:00Z
- F6.3 Promotion gate — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T26:30:00Z

---

## Agent Registry

| Agent ID | Type | Assigned Features | Last Active |
|----------|------|-------------------|-------------|
| ai-nemotron-ses_eaa59d66 | AI | F1.1, F1.2, F1.3, F1.4, F1.5, F1.6, F1.7, F3.1 | 2026-10-20T23:30:00Z |
| ai-nemotron-ses_eaa6f421 | AI | F0.x, F2.1-F2.11, F3.2-F3.9 | 2026-10-20T12:00:00Z |
| ai-longcat-ses_ea89089b | AI | F4.1, F5.1, F5.2, F5.3, F5.4 | 2026-10-20T22:30:00Z |
| ai-minimax-m3.1-flash-ses_ea89089b | AI | F5.5, F5.6, Phase 5 integration | 2026-10-20T45:00:00Z |

---

## License & Data Source Compliance Log

| Date | Action | Source/Library | License | Status |
|------|--------|----------------|---------|--------|
| 2026-10-20 | Added dependency | aiosqlite | MIT | Approved (test dependency) |
| 2026-10-20 | Added dependency | numpy (core dependency for the Monte Carlo engine) | BSD-3-Clause | Approved - already listed in PLAN.md Appendix A |
| 2026-10-20 | Added data source | Synthetic generator (in-house, `ml/synthetic`) | MIT (project license) | Approved - every row tagged `is_synthetic=true` |
| 2026-10-20 | Added data source | Synthetic price source (in-house, log-normal) | MIT (project license) | Approved - `source=synthetic`, `is_synthetic=true` |
| 2026-10-20 | Added dependency | fake-indexeddb (IndexedDB shim for the F5.5 offline store tests) | Apache-2.0 | Approved - dev-only, see ADR-004 |

---

## ADR Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-001 | Technology Stack Selection | Accepted | 2026-10-20 |
| ADR-002 | Decision Engine Design | Accepted | 2026-10-20 |
| ADR-003 | Market Intelligence Design | Accepted | 2026-10-20 |
| ADR-004 | Offline inspection storage and the fake-indexeddb test shim | Accepted | 2026-10-20 |

---

*Last updated: 2026-10-20*
*Next review: Before starting Phase 3 work*