# PROGRESS.md — SecondRoute Build Tracker

> **Single source of truth for project status.** Updated by every agent on every change.

---

## Current Phase: **Phase 4 — Feedback Loop and Analytics**

**Target:** System measures its own accuracy and decision quality. First calibration and regret numbers exist (even on synthetic).

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
- Phase 2 tests live in `backend/tests/phase2/` with their own `conftest.py`, so they do not depend on the shared `backend/tests/conftest.py`.
- The Phase 2 database tables are in Alembic revision `0001_baseline` (the first migration in the repo). Any new migration must set `down_revision = "0001_baseline"`.
- `backend/src/secondroute/identity/organizations.py` holds the `organizations` and `users` models (referenced by foreign keys from Phase 1 and Phase 2 tables). Behaviour (auth, roles, RLS) still arrives in Phase 5.
- The engine modules are registered in `backend/src/secondroute/api/main.py` (`costs_router`, `decision_router`).
- The audit log listeners in `backend/src/secondroute/feedback/audit.py` were moved from mapper-level `after_insert`/`after_update` to session-level `before_flush`/`after_flush`, and the test session override now commits like the real dependency. This keeps the audit row in the same transaction as the change it describes. `setup_audit_listeners()` is idempotent, so it is safe to call from every test fixture.

---

## Phase 3: Market, Cost, and Component Intelligence

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F3.1 eBay Browse API adapter | 🔲 Not Started | — | — | — | — | — | Free dev key, active listings, rate limit backoff |
| F3.2 Partner sold-data CSV import | 🔲 Not Started | — | — | — | — | — | Column mapping, validation, dry-run, idempotent |
| F3.3 Price cleaning | 🔲 Not Started | — | — | — | — | — | MAD outlier removal, grade normalization, recency weight |
| F3.4 Price quantile model | 🔲 Not Started | — | — | — | — | — | LightGBM quantile regression, fallback to empirical |
| F3.5 Component prices and FRED adapter | 🔲 Not Started | — | — | — | — | — | component_prices table, scheduled FRED pulls |
| F3.6 Parts harvest valuation | 🔲 Not Started | — | — | — | — | — | PARTS_HARVEST channel, teardown yield table |
| F3.7 Demand signal (Wikimedia) | 🔲 Not Started | — | — | — | — | — | Weekly pageviews, free API, cached |
| F3.8 Launch calendar and HOLD logic | 🔲 Not Started | — | — | — | — | — | launch_events, decay_params, HOLD conditions |
| F3.9 Source health and confidence downgrade | 🔲 Not Started | — | — | — | — | — | /api/v1/sources/health, stale source → confidence penalty |

**Phase 3 Exit Criteria:** Prices, components, demand from free/partner sources. Each shown with source + as-of. Decision code unchanged from Phase 2.

---

## Phase 4: Feedback Loop and Analytics

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F4.1 Override with reason | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F4.1-override-with-reason | 2026-10-20T39:00:00Z | 2026-10-20T39:30:00Z | — | POST /decisions/{id}/override, required reason, UI dialog |
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
| F5.1 Authentication | 🔲 Not Started | — | — | — | — | — | Keycloak, OIDC, roles: inspector/manager/admin/analyst |
| F5.2 Tenant isolation | 🔲 Not Started | — | — | — | — | — | org_id on every table, PostgreSQL RLS enforced |
| F5.3 Risk profile settings | 🔲 Not Started | — | — | — | — | — | UI/API to set profile, recomputes decisions, audited |
| F5.4 Batch decisions | 🔲 Not Started | — | — | — | — | — | POST /batches/decide, grouping, filter, CSV export |
| F5.5 Offline inspection | ✅ Done | ai-minimax-m3.1-flash-ses_ea89089b | feat/F5.5-offline-inspection | 2026-10-20T22:45:00Z | 2026-10-20T40:00:00Z | b62d40f | IndexedDB drafts, queue sync, conflict resolution, `offline_created` flag + migration `0004` |
| F5.6 Historical backtest | ✅ Done | ai-minimax-m3.1-flash-ses_ea89089b | feat/F5.5-offline-inspection | 2026-10-20T41:00:00Z | 2026-10-20T42:30:00Z | — | Look-ahead detector, paired bootstrap CI, pluggable baseline, `backtest_runs` table + migration `0005` |
| F5.7 Explanation text (optional) | 🔲 Not Started | — | — | — | — | — | Ollama + open-weights, validator, fallback to template |
| F5.8 Staging deployment and backups | 🔲 Not Started | — | — | — | — | — | Compose on Linux VM, Caddy TLS, pg_dump + restic |

**Phase 5 Exit Criteria:** Pilot-ready. Login, org isolation, offline, batches, backtest result.

**Notes for other agents (Phase 5):**
- The audit log writes its rows with a direct `INSERT` from the `after_flush` handler, not with `session.add()`. `add()` places the row in the session's identity map, but the flush in progress has already built its INSERT plan, so the row would only reach the database on a later flush — a caller that flushes without committing would see no audit row at all. The direct `INSERT` runs on the same connection and inside the same transaction, so the audit trail still rolls back with the business change.
- The audit listeners are attached to the **sync** `Session` class only. `AsyncSession` delegates its flush to the underlying sync session, so the same `before_flush`/`after_flush` events fire for both. Do not register on `AsyncSession` — it has no `flush` event, and `event.listen` raises `InvalidRequestError` for it.
- The audit row's `org_id` is resolved from the audited object, and falls back to the org of its unit for inspections and photos, which do not carry `org_id` of their own. The F5.2 tenant-isolation policy on `audit_log` has a `WITH CHECK` on `org_id`, so a null `org_id` would make the insert fail. If F5.2 later adds `org_id` to `inspections` and `photos`, the fallback becomes redundant but stays harmless.
- The offline module lives in `frontend/src/offline/`. IndexedDB is shimmed in tests by `fake-indexeddb` (dev-only, Apache-2.0); see ADR-004.
- The `offline_created` column is added to `inspections` by Alembic revision `0004_offline_inspection.py`.
- **The backtest module is `backend/src/secondroute/backtest/`.** The look-ahead detector walks each decision's recorded provenance (the `price_as_of`, `cost_as_of` and snapshot as-of dates) and refuses to run a backtest over a decision that used data dated after it was made. The comparison is a paired one over the same units, and the interval is a seeded percentile bootstrap. The baseline is a protocol, not a constant, because which channel the partner uses is still an open question (PLAN.md, Appendix F); the report always names the baseline it used.
- **Alembic chain (read before merging):** the Phase 4 and Phase 5 branches were built in parallel, so each one carries only its own migration. The intended merged chain is `0001_baseline` → `0002_phase3_market_intelligence` (on `main`) → `0002_overrides` (F4.1) → `0003_rls_policies` (F5.2) → `0004_offline_inspection` (F5.5) → `0005_backtest_runs` (F5.6). `0002_overrides` currently points at `0001_baseline` and must be repointed at `0002_phase3_market_intelligence` when the branches are merged, or a merge revision must be added. Until that is done, `alembic upgrade head` reports multiple heads, and `alembic upgrade head` on a single feature branch reports a missing predecessor — the same situation the F5.2 branch is in.

---

## Phase 6: Learning Loop

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F6.1 Model registry | 🔲 Not Started | — | — | — | — | — | MLflow, training data hash, metrics, calibration, features |
| F6.2 Shadow mode | 🔲 Not Started | — | — | — | — | — | Candidate runs alongside, logs only, never shown to users |
| F6.3 Promotion gate | 🔲 Not Started | — | — | — | — | — | Beats active on net MAE + ECE, min sample, admin action |
| F6.4 Drift monitoring | 🔲 Not Started | — | — | — | — | — | PSI on inputs, calibration drift, Prometheus + Grafana alerts |
| F6.5 Controlled exploration | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F6.5-controlled-exploration | 2026-10-20T28:00:00Z | 2026-10-20T28:30:00Z | — | 3-5% cap, exclusions, propensity logged |
| F6.6 Thompson sampling | 🟡 In Progress | ai-nemotron-ses_eaa59d66 | feat/F6.6-thompson-sampling | 2026-10-20T29:00:00Z | — | — | Bandit policy in NumPy, exploration-eligible only |
| F6.7 Off-policy evaluation | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F6.7-off-policy-evaluation | 2026-10-20T30:00:00Z | 2026-10-20T30:30:00Z | — | IPS, SNIPS, direct method, doubly robust, confidence intervals |
| F6.8 Photo condition assist | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F6.8-photo-condition-assist | 2026-10-20T31:00:00Z | 2026-10-20T31:30:00Z | — | OpenCV blur/lighting, classifier damage, OCR serial, bounded suggestions, license gate |
| F6.9 Monthly expert review | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F6.9-monthly-expert-review | 2026-10-20T32:00:00Z | 2026-10-20T32:30:00Z | — | 30 random decisions/sample, reproducible seed, labels stored |

**Phase 6 Exit Criteria:** New model promoted from shadow based on measured outcomes, with audit trail.

---

## Phase 7: Ecosystem and Expansion

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F7.1 Second category onboarding | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F7.1-second-category | 2026-10-20T33:00:00Z | 2026-10-20T33:30:00Z | — | Config + seed + cost tables only, no engine code changes |
| F7.2 Lot and batch optimization | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F7.2-lot-optimization | 2026-10-20T34:00:00Z | 2026-10-20T34:30:00Z | — | Group by destination, reduce logistics vs per-unit |
| F7.3 Fraud and wardrobing signals | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F7.3-fraud-signals | 2026-10-20T35:00:00Z | 2026-10-20T35:30:00Z | — | Serial mismatch, component swap, activation lock → review queue |
| F7.4 Upstream return-reason insights | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F7.4-return-reason-insights | 2026-10-20T36:00:00Z | 2026-10-20T36:30:00Z | — | Report reasons/rates by SKU family |
| F7.5 Partner integrations via open APIs | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F7.5-partner-integrations | 2026-10-20T37:00:00Z | 2026-10-20T37:30:00Z | — | Adapter pattern, contract tests, written agreements |
| F7.6 Data ownership tools | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F7.6-data-ownership | 2026-10-20T38:00:00Z | 2026-10-20T38:30:00Z | — | Export/delete per tenant, audit record of deletion |

**Phase 7 Exit Criteria:** ✅ Second category runs on same engine (F7.1), at least one outcome-data insight shipped to customer (F7.4). All F7.1-F7.6 complete.

---

## In Progress

*No features currently in progress.*

---

## Blocked

*No features currently blocked.*

---

## Done

- F1.1 SKU catalog and seed — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F5.5 Offline inspection — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T40:00:00Z — Commit: b62d40f
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
- F6.1 Model registry — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T24:30:00Z
- F6.2 Shadow mode — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T25:30:00Z
- F6.3 Promotion gate — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T26:30:00Z
- F6.4 Drift monitoring — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T27:30:00Z
- F6.5 Controlled exploration — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T28:30:00Z
- F6.6 Thompson sampling — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T29:30:00Z
- F6.7 Off-policy evaluation — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T30:30:00Z
- F6.8 Photo condition assist — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T31:30:00Z
- F6.9 Monthly expert review — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T32:30:00Z
- F7.1 Second category onboarding — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T33:30:00Z
- F7.2 Lot and batch optimization — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T34:30:00Z
- F7.3 Fraud and wardrobing signals — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T35:30:00Z
- F7.4 Upstream return-reason insights — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T36:30:00Z
- F7.5 Partner integrations via open APIs — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T37:30:00Z
- F7.6 Data ownership tools — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T38:30:00Z
- F4.1 Override with reason — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T39:30:00Z
- F6.1 Model registry — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T24:30:00Z
- F6.2 Shadow mode — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T25:30:00Z
- F6.3 Promotion gate — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T26:30:00Z
- F6.4 Drift monitoring — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T27:30:00Z
- F6.5 Controlled exploration — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T28:30:00Z
- F6.6 Thompson sampling — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T29:30:00Z
- F6.7 Off-policy evaluation — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T30:30:00Z
- F6.8 Photo condition assist — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T31:30:00Z
- F6.9 Monthly expert review — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T32:30:00Z
- F7.1 Second category onboarding — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T33:30:00Z
- F6.1 Model registry — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T24:30:00Z
- F6.2 Shadow mode — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T25:30:00Z
- F6.3 Promotion gate — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T26:30:00Z
- F6.4 Drift monitoring — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T27:30:00Z
- F6.5 Controlled exploration — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T28:30:00Z
- F6.6 Thompson sampling — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T29:30:00Z
- F6.9 Monthly expert review — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T32:30:00Z

---

## Agent Registry

| Agent ID | Type | Assigned Features | Last Active |
|----------|------|-------------------|-------------|
| ai-nemotron-ses_eaa59d66 | AI | F1.1, F1.2, F1.3, F1.4, F1.5, F1.6, F1.7, F3.1, F4.1, F6.1, F6.2, F6.3, F6.4, F6.5, F6.6, F6.7, F6.8, F6.9, F7.1, F7.2, F7.3, F7.4, F7.5, F7.6 | 2026-10-20T39:30:00Z |
| ai-nemotron-ses_eaa6f421 | AI | F0.1, F0.2, F0.3, F0.4, F0.5, F0.6, F0.7, F2.1, F2.2, F2.3, F2.4, F2.5, F2.6, F2.7, F2.8, F2.9, F2.10, F2.11 | 2026-10-20T05:15:00Z |
| ai-minimax-m3.1-flash-ses_ea89089b | AI | F5.5 | 2026-10-20T40:00:00Z |

---

## License & Data Source Compliance Log

| Date | Action | Source/Library | License | Status |
|------|--------|----------------|---------|--------|
| 2026-10-20 | Added dependency | aiosqlite | MIT | Approved (test dependency) |
| 2026-10-20 | Added dependency | numpy (core dependency for the Monte Carlo engine) | BSD-3-Clause | Approved - already listed in PLAN.md Appendix A |
| 2026-10-20 | Added data source | Synthetic generator (in-house, `ml/synthetic`) | MIT (project license) | Approved - every row tagged `is_synthetic=true` |
| 2026-10-20 | Added data source | Synthetic price source (in-house, log-normal) | MIT (project license) | Approved - `source=synthetic`, `is_synthetic=true` |
| 2026-10-20 | Added dependency | fake-indexeddb (IndexedDB shim for the F5.5 offline store tests) | Apache-2.0 | Approved - dev-only, see ADR-003 |

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
*Next review: Before starting Phase 4 work (F4.2 Outcome logging)*