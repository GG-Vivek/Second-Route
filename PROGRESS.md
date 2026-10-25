# PROGRESS.md — SecondRoute Build Tracker

> **Single source of truth for project status.** Updated by every agent on every change.

---

## Current Phase: **Phase 11 — Accounts, categories and the glass surfaces** is complete.
Phase 8 rebuilt the whole user interface on one design system and turned the
decision card into a spatial decision console. Phase 9 measured the colours
rather than eyeballing them, put the cache up, gave the application something
to look at, and closed the defects that came out of it. Phase 10 built the
other half of the product: a shop window, on its own port, that a buyer can
look at without ever seeing the business. Phase 11 gave the application a door
to walk through and a catalogue that is no longer laptops alone.

**Target:** a retailer can sign up, the window shows the kinds of device a
shop shows, and a device with no battery is not graded as one with a dead
battery.

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
| F1.7 Audit log | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase5-integration | 2026-10-20T20:15:00Z | 2026-10-20T49:00:00Z | e1d32aa | Model, read-only API, the actor is the user, outcomes audited, one row per mutation |

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
| F4.1 Override with reason | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T10:00:00Z | 2026-10-20T17:57:00Z | 9b217b0 | POST /decisions/{id}/override, required reason, UI dialog |
| F4.2 Outcome logging | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T17:52:00Z | 2026-10-20T17:58:00Z | 7711b82 | POST /units/{id}/outcome, append-only, linked to decision |
| F4.3 Predicted vs realized view | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T17:53:00Z | 2026-10-20T17:59:00Z | 8617b55 | Residual, in-range flag per unit |
| F4.4 Time-to-sell model | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T18:05:00Z | 2026-10-20T18:08:00Z | 51182d8 | Kaplan-Meier by channel/grade, fallback to prior |
| F4.5 Regret calculation | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T18:09:00Z | 2026-10-20T18:20:00Z | — | Observed + estimated (labeled), never summed silently |
| F4.6 Calibration | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T18:35:00Z | 2026-10-20T18:50:00Z | — | Reliability curve, ECE, isotonic recalibration (versioned) |
| F4.7 Analytics page | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T18:55:00Z | 2026-10-20T19:05:00Z | — | North star, regret over time, calibration, override rate |
| F4.8 Data export | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T19:10:00Z | 2026-10-20T19:20:00Z | — | CSV export decisions/overrides/outcomes, round-trip |

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
| F5.7 Explanation text (optional) | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase5-integration | 2026-10-20T50:00:00Z | 2026-10-20T52:00:00Z | — | Ollama + qwen2.5, the number validator, fallback to the template, explanations stored |
| F5.8 Staging deployment and backups | ✅ Done | ai-minimax-m3.1-flash-ses_ea89089b | feat/phase5-integration | 2026-10-20T47:00:00Z | 2026-10-20T48:30:00Z | — | Staging Compose stack with Caddy TLS, daily pg_dump + restic, and a restore drill that reproduces the row counts |

**Notes for other agents (Phase 5):**
- **`make dev` starts the whole application.** It checks the prerequisites, prepares the database, runs the migrations, seeds the catalogue and a development organisation, and starts the API and the frontend; Ctrl-C stops both. `scripts/dev.sh` is the implementation and `make help` lists the other targets. The paths it uses are relative to the repository root.
- **`uv sync` needs `--all-extras`.** The `dev` group alone is not enough: the extras carry the testing, machine-learning and vision dependencies, and a plain `uv sync` prunes them. Two of the pruned packages were load-bearing without being declared - `greenlet`, which SQLAlchemy's asyncio support needs, and `python-jose`, which the auth module imports. The application's ability to start depended on the `pipelines` extra, and the backend image (`uv sync --frozen --no-dev`) could not start at all. Both are declared now, and the CI checks that the core dependencies alone can import the application.
- The Alembic chain is a single line. `0001_baseline` → `0002_phase3_market_intelligence` → `0003_feedback_tables` → `0004_rls_policies` → `0005_offline_inspection` → `0006_backtest_runs` → `0007_regret_measurements` → `0008_learning_tables`. `0003_feedback_tables` creates the `overrides` and `outcomes` tables together, which is what makes the chain linear without a merge revision. `alembic upgrade head`, `downgrade base` and `upgrade head` again all run clean against a real PostgreSQL.
- `0008_learning_tables` creates `shadow_predictions`, `promotion_records` and `expert_review_labels`. Those three models existed before the consolidation but had no migration, so a database built from the migrations was missing them and the endpoints that write to them would have failed.
- `alembic check` still reports four index-name differences against the models (`audit_log.actor`/`created_at`, `audit_log.entity`/`entity_id`, `audit_log.org_id`/`created_at`, `skus.family`/`model_name`). These are pre-existing: the baseline migration names its indexes differently from the models. Nothing reads them by name, and they are not a correctness problem.
- The audit log writes its rows with a direct `INSERT` from the `after_flush` handler, not with `session.add()`. `add()` places the row in the session's identity map, but the flush in progress has already built its INSERT plan, so the row would only reach the database on a later flush — a caller that flushes without committing would see no audit row at all. The direct `INSERT` runs on the same connection and inside the same transaction, so the audit trail still rolls back with the business change.
- The audit listeners are attached to the **sync** `Session` class only. `AsyncSession` delegates its flush to the underlying sync session, so the same `before_flush`/`after_flush` events fire for both. Do not register on `AsyncSession` — it has no `flush` event, and `event.listen` raises `InvalidRequestError` for it.
- The audit row's `org_id` is resolved from the audited object: directly when it has one, through its unit for an inspection or a photo, through its decision for an override, and from its own id for an organisation. The tenant-isolation policy on `audit_log` checks `org_id` on every write, so a null `org_id` would make the insert fail.
- The organisation context has to be set in **both** places: `set_session_org_id` sets the Python context variable that the application filter reads, and the PostgreSQL setting `app.current_org_id` that the policies read. Setting only one leaves the isolation half-implemented.
- The application must connect to PostgreSQL as a role that is **not** a superuser and does not have `BYPASSRLS`: PostgreSQL bypasses row-level security for those roles whatever the policies say. `docker/postgres/01-create-app-role.sh` creates the role in Compose, and `backend/scripts/create_app_role.py` does the same in CI.
- The application runs the Alembic migrations at startup, not `create_all`: the migrations are where the tenant-isolation policies live, and a schema built any other way would have the tables but none of the isolation.
- The offline module lives in `frontend/src/offline/`. IndexedDB is shimmed in tests by `fake-indexeddb` (dev-only, Apache-2.0); see ADR-004.
- **The backups need a second database role.** `pg_dump` refuses to dump a table whose rows the tenant-isolation policies would filter, so a backup taken with the application's role fails outright. The staging stack therefore has a `secondroute_app_backup` role with `BYPASSRLS`, which is a member of the application role. The `BYPASSRLS` attribute is not inherited upwards, so the application keeps the policies. `docker/postgres/01-create-app-role.sh` creates both roles.
- The restore drill is `scripts/verify_restore.sh`, and it runs as a test: `backend/tests/phase5/test_backup_restore.py`. It takes a backup, restores it into a fresh database, compares the row counts of every table and starts the application against the result. It skips when PostgreSQL, `pg_dump` or restic are not available. The runbook is `docs/runbooks/restore.md`.
- The backtest module is `backend/src/secondroute/backtest/`. The look-ahead detector walks each decision's recorded provenance (the `price_as_of`, `cost_as_of` and snapshot as-of dates) and refuses to run a backtest over a decision that used data dated after it was made. The comparison is a paired one over the same units, and the interval is a seeded percentile bootstrap. The baseline is a protocol, not a constant, because which channel the partner uses is still an open question (PLAN.md, Appendix F); the report always names the baseline it used.

**Phase 5 Exit Criteria:** Pilot-ready. Login, org isolation, offline, batches, backtest result.
✅ Every gate item is now met: auth, tenant isolation, offline, batch decisions, the backtest, and the staging deployment with backups.
⏳ The staging stack has not been run on a Linux VM. The scripts, the stack and the restore drill are verified; the VM itself needs a host.
✅ Auth, tenancy, offline and backtest are done and integrated on `feat/phase5-integration`.
Phase 5 is complete. The staging deployment (F5.8) is done, and the restore drill has been
run against a real PostgreSQL.

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
| F6.1 Model registry | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T24:00:00Z | 2026-10-20T24:30:00Z | 8e4e366 | MLflow, training data hash, metrics, calibration, features |
| F6.2 Shadow mode | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T24:30:00Z | 2026-10-20T25:30:00Z | 8e4e366 | Candidate runs alongside, logs only, never shown to users |
| F6.3 Promotion gate | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/F6.3-promotion-gate | 2026-10-20T26:00:00Z | 2026-10-20T26:30:00Z | — | Beats active on net MAE + ECE, min sample, admin action |
| F6.4 Drift monitoring | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T27:00:00Z | 2026-10-20T27:30:00Z | 8e4e366 | PSI on inputs, calibration drift, Prometheus + Grafana alerts |
| F6.5 Controlled exploration | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T28:00:00Z | 2026-10-20T28:30:00Z | 8e4e366 | 3-5% cap, exclusions, propensity logged |
| F6.6 Thompson sampling | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T29:00:00Z | 2026-10-20T29:30:00Z | 8e4e366 | Bandit policy in NumPy, exploration-eligible only |
| F6.7 Off-policy evaluation | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T30:00:00Z | 2026-10-20T30:30:00Z | 8e4e366 | IPS with confidence intervals |
| F6.8 Photo condition assist | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T31:00:00Z | 2026-10-20T31:30:00Z | 8e4e366 | OpenCV blur/lighting, classifier damage, OCR serial, bounded suggestions |
| F6.9 Monthly expert review | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T32:00:00Z | 2026-10-20T32:30:00Z | 8e4e366 | 30 random decisions/sample, reproducible seed, labels stored |

**Phase 6 Exit Criteria:** New model promoted from shadow based on measured outcomes, with audit trail.

---

## Phase 7: Ecosystem and Expansion

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F7.1 Second category onboarding | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T33:00:00Z | 2026-10-20T33:30:00Z | 26f2bbf | Config + seed + cost tables only, no engine code changes |
| F7.2 Lot and batch optimization | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T34:00:00Z | 2026-10-20T34:30:00Z | 26f2bbf | Group by destination, reduce logistics vs per-unit |
| F7.3 Fraud and wardrobing signals | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T35:00:00Z | 2026-10-20T35:30:00Z | 26f2bbf | Serial mismatch, component swap, activation lock → review queue |
| F7.4 Upstream return-reason insights | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T36:00:00Z | 2026-10-20T36:30:00Z | 26f2bbf | Report reasons/rates by SKU family |
| F7.5 Partner integrations via open APIs | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T37:00:00Z | 2026-10-20T37:30:00Z | 26f2bbf | Adapter pattern, contract tests, written agreements |
| F7.6 Data ownership tools | ✅ Done | ai-nemotron-ses_eaa59d66 | feat/phase6-phase7-learning | 2026-10-20T38:00:00Z | 2026-10-20T38:30:00Z | 26f2bbf | Export/delete per tenant, audit record of deletion |

**Phase 7 Exit Criteria:** Second category runs on same engine, at least one outcome-data insight shipped to customer.

---

## Phase 8: Product surface

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F8.0 Design decision and dependency licences | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.0-design-decision-and-licences | 2026-10-21T00:00:00Z | 2026-10-21T01:00:00Z | 26eafec | ADR-006, Phase 8 in PLAN.md, CHANGELOG.md created |
| F8.1 Design tokens, theme and self-hosted fonts | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.1-design-tokens | 2026-10-21T01:00:00Z | 2026-10-21T02:10:00Z | 6ae79a0 | MD3 token set, theme provider, @fontsource packages, 10 tests |
| F8.2 The interface kit | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.2-ui-kit | 2026-10-21T02:10:00Z | 2026-10-21T03:10:00Z | 67e4a5a | 19 primitives, 31 tests |
| F8.3 The application shell | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.3-app-shell | 2026-10-21T03:10:00Z | 2026-10-21T04:05:00Z | 853bd92 | Sidebar, glass header, command palette, 12 tests |
| F8.4 The decision distribution endpoint | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.4-decision-distribution | 2026-10-21T04:05:00Z | 2026-10-21T05:20:00Z | bf84e83 | GET /decisions/{id}/distribution, 15 tests, fixed the replay defect |
| F8.5 The channel landscape and the decision card | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.5-channel-landscape | 2026-10-21T05:20:00Z | 2026-10-21T07:20:00Z | f81e93e | 2D ridgeline, the R3F scene, the rebuilt card, 167 tests |
| F8.6 Intake, inspection and unit surfaces | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.6-intake-and-units | 2026-10-21T07:20:00Z | 2026-10-21T08:40:00Z | fef4f9c | Stepped forms, the unit tabs, the photographs, the SKU fix |
| F8.7 Dashboard, health, analytics and backtest surfaces | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.7-dash-and-analytics | 2026-10-21T08:40:00Z | 2026-10-21T09:40:00Z | 2cfbf67 | The north star, the reliability curve, the data sources, the health fix |
| F8.8 Motion, accessibility and the visual regression suite | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.8-motion-and-a11y | 2026-10-21T09:40:00Z | 2026-10-21T10:40:00Z | 192461e | The Playwright suite, the keyboard pass, the CI job, 24 end-to-end tests |

**Phase 8 Exit Criteria:** ✅ One design system, one decision console, and a test suite that proves both. 169 frontend unit tests, 26 end-to-end tests, 896 backend tests.

---

## Phase 9: The colours, the cache and the data

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F9.1 The colour grading | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.5-channel-landscape | 2026-10-21T11:00:00Z | 2026-10-21T12:20:00Z | 5c807ed | The MD3 on-pattern for the badges, 44 measured pairs |
| F9.2 The cache | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.5-channel-landscape | 2026-10-21T12:20:00Z | 2026-10-21T12:40:00Z | 42971d7 | Redis installed and running, three states told apart |
| F9.3 The photographs and the data | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.5-channel-landscape | 2026-10-21T12:40:00Z | 2026-10-21T13:30:00Z | 543ad4b | The upload, the EXIF stripping, the seed, the proxies |
| F9.4 The defects | ✅ Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F8.5-channel-landscape | 2026-10-21T13:30:00Z | 2026-10-21T15:00:00Z | 71b0b28, 34f3487, d7426c3 | Fifteen defects, the isolation among them |

**Phase 9 Exit Criteria:** ✅ The colours are measured, the cache is up, there is data and there are photographs, and the defects are closed. 169 frontend unit tests, 26 end-to-end tests, 910 backend tests.

**Notes for other agents:**
- **The isolation did not bind on two tables.** A policy only applies to the owner of a table when `FORCE ROW LEVEL SECURITY` is set, and the application role owns every table. Migration `0013_force_rls` fixes it, and the test that checks the migrations against the models would not have caught it: the gap was between the policy and the role, not between the model and the schema.
- **The database enums had drifted from the models.** A native enum on PostgreSQL only holds the values it was created with, and the baseline created the three intake enums before the models grew. Four return reasons, two order channels and four unit statuses were refused by the database, and the intake form offered all of them. The test suite could not see it, because SQLite treats a native enum as a string with a hint attached.
- **The `set_session_org_id` setting is transaction-local.** A commit clears it. Anything the request does after the commit runs with no tenant. `commit_with_tenant` puts it back.
- **A relationship that is loaded on demand raises in an asynchronous session** when it is touched outside a greenlet, which becomes a five hundred in the middle of a request. The intake relationships are loaded with the unit now.
- **The photographs are served from `/uploads`.** The development server and the proxy in front of the stack both have to route it, or the browser is given the page itself where it asked for an image.
- **The demonstration data is cleared by `python scripts/seed_demo_data.py --reset`.** The reset names the organisation first; without it the policies match nothing and the delete does nothing.

**Phase 8 Exit Criteria:** One design system, one decision console, and a test suite that proves both.

**Notes for other agents:**
- Phase 8 changes only the frontend, except F8.4, which adds one read-only backend endpoint. No decision logic, no schema change, no migration.
- The 3D code is isolated under `frontend/src/three/` and is reached only through a dynamic `import()`. If the react-three-fiber upgrade to v9 and React 19 ever happens, that directory is the blast radius.
- `three` is pinned below 0.186 on purpose: 0.186 removed the shadow map type that react-three-fiber v8 selects by default.
- The existing `data-testid` contracts in the decision card tests are part of the interface. A redesign that renames one of them has to change the test in the same commit, on purpose, never silently.
- **Known defect, carried into Phase 8:** the dashboard calls `/api/v1/health`, but the backend serves `/health` at the root, so the landing page shows "Request failed with status code 404" on every load. This predates Phase 8 and is fixed in F8.7 when the dashboard is rebuilt. The health check never passed from the browser; the F0.4 acceptance criterion was met against the endpoint directly.
- **Known debt, not in Phase 8:** `npm audit` reports 17 findings, all in the dev toolchain (vitest, vite, tailwindcss, react-router-dom). Every fix is a major version bump. None came from the Phase 8 dependencies. Migrating the toolchain is a separate piece of work and must not be bundled into a design change.
- **Fixed in F8.4, and it was a real defect:** the `reproduce` endpoint replayed a decision without binding the price source to the SKU family, without valuing the parts, and without consulting the launch calendar. It looked like a faithful replay and was not one: it priced the unit as a different model. The confidence came back as 0.8159 where the stored decision said 0.8125. The live path and the replay path now both go through `build_price_context` in `decision/engine.py`, so they cannot drift apart again. The existing test only asserted that the recommended channel matched, which it did; the mismatch was in the numbers underneath.
- **Fixed in F8.5, also a real defect:** `DecisionPage` fetched the decision with `activeDecisionId`, which is null until the operator clicks a row in the history. The card therefore never appeared on its own; the page showed the history and nothing else. The query now uses the decision that is being shown.
- **Fixed in F8.5, a gap in Phase 5 rather than a bug:** the frontend never named a tenant. The backend accepts the organisation in the `X-Org-Id` header outside production, and the frontend never sent it, so every write from the browser was refused with `tenant_not_resolved` and every read came back empty. The client now sends the header, taken from `VITE_ORG_ID` or from local storage. The real login still has to set the tenant from the token; that is Phase 5 work and is not done.
- **Fixed in F8.6, and it had always been broken:** the API never returned the model of a unit, so every list said "Unknown" and the unit detail had an empty section for it. The model is loaded with the unit now.
- **Fixed in F8.6, and it had always been broken:** a photo record carries the path the photograph is at, and nothing ever served it. The upload directory is mounted and the photographs are shown.
- **Fixed in F8.7, and it had always been broken:** the dashboard asked for `/api/v1/health`, but the health endpoint is at the root of the service. Every load of the dashboard showed an error.

---

## Phase 10: The shop window

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---|---|---|---|---|---|---|---|
| F10.1 The public listings | Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F10.1-public-listings | 2026-10-21T10:30:00Z | 2026-10-21T12:30:00Z | 89d65c4 | `GET /api/v1/public/listings` and the device's own page |
| F10.2 The shop window | Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F10.2-the-shop-window | 2026-10-21T12:30:00Z | 2026-10-21T13:30:00Z | (this commit) | `frontend-public/`, on port 5174 |
| F10.3 The window in the stack | Done | ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | feat/F10.3-the-window-in-the-stack | 2026-10-21T13:30:00Z | 2026-10-21T13:30:00Z | (this commit) | The compose stack, the staging stack and the CI |

**Notes on Phase 10**

- **The design system is shared, not copied.** The tokens, the nineteen primitives, the theme provider and the Tailwind scale live in `frontend/src` and are reached through a path alias. The console is unchanged; a copy of the token set would have been a second token set that disagrees.
- **The window is public.** There is no sign-in and no operator's surface behind it. `PUBLIC_ORG_ID` decides whose stock it shows, and a caller cannot choose.
- **A photograph says whether it may be published.** One of the four angles the inspection form takes is a photograph of the label on the bottom of the device, and the label carries the serial number. The serial was not in the response, but it was in the picture.
- **Fixed in F10.1, and it had always been broken:** the seed marked every unit sold as soon as the first one was sold, because it read the running total of the outcomes rather than the outcome of the unit. Nothing was ever left on the shelf.
- **Fixed in F10.1, a trap worth knowing about:** a generator dependency that sits underneath another dependency is torn down as soon as the outer one returns, and the session dependency clears the organisation when it is torn down. The storefront therefore had a session with no organisation on it, and every row was refused.

---

## Phase 11: Accounts, categories and the glass surfaces

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---|---|---|---|---|---|---|---|
| F11.1 Accounts | Done | human-ui-ux-designer | (reference build `hackyard_Build_2026_v2`) | 2026-10-24T00:00:00Z | 2026-10-25T00:00:00Z | (this commit) | `POST /auth/signup/retailer`, `/auth/signup/user`, `/auth/signin`; migration `0017_accounts`; console sign-up and sign-in pages |
| F11.2 The mixed catalogue | Done | human-ui-ux-designer + ai-mimo-ses_e90b81ea6ffe | (reference build) | 2026-10-24T00:00:00Z | 2026-10-25T00:00:00Z | (this commit) | `identity/categories.py`, 37 seed rows; mixer grinders, air conditioners, air purifiers and hair dryers added on top of the reference build |
| F11.3 The window shows the kinds | Done | human-ui-ux-designer | (reference build) | 2026-10-24T00:00:00Z | 2026-10-25T00:00:00Z | (this commit) | Category filter with counts, per-category icons, debounced search |
| F11.4 Devices without a battery | Done | human-ui-ux-designer | (reference build) | 2026-10-24T00:00:00Z | 2026-10-25T00:00:00Z | (this commit) | Nullable battery reading, `NO_BATTERY_SCORE` at the middle of the scale |
| F11.5 The backdrop | Done | human-ui-ux-designer | (reference build) | 2026-10-24T00:00:00Z | 2026-10-25T00:00:00Z | (this commit) | `components/visual/ShaderBackdrop.tsx` |
| F11.6 The glass surfaces | Done | human-ui-ux-designer | (reference build) | 2026-10-24T00:00:00Z | 2026-10-25T00:00:00Z | (this commit) | `components/visual/LiquidGlass.tsx` and the `glass-panel` / `glass-card` layers |
| F11.7 The colour, and what it carries | Done | ai-mimo-ses_e90b81ea6ffe | main | 2026-10-24T23:11:44Z | 2026-10-25T00:00:00Z | (this commit) | Light is the default; the dark theme is a teal ink rather than a near-black; `src/theme/meaning.ts` says what each hue means; the contrast suite measures `index.css` instead of a copy of it; ADR-008 |

**Notes on Phase 11**

- **The work arrived as a reference build.** A UI/UX designer worked in `hackyard_Build_2026_v2`, a second clone of this repository, and left it uncommitted. It was merged into the main tree file by file (tracked changes by patch, new files copied), so the designer's history and this repository's are one.
- **Four categories were added after the merge** — mixer grinders, air conditioners, air purifiers and hair dryers — because the reference build did not have them. Each needed a category record, seed rows, a silhouette and two drawings, and an icon.
- **Two tests were rewritten, not weakened.** `test_from_inspection_handles_missing_values` and `test_from_inspection_handles_bad_battery` asserted that a missing battery reading reads as `0.0`. The reading is now absent rather than zero, so they assert that, and that an unreadable reading is treated exactly as an absent one.
- **Fixed with the merge:** six type errors the new code introduced (the mypy run went from 16 errors to none), one lint error from a 23-branch drawing function (split into a dispatch table), and two sign-in tests that looked up a required field by its bare label while the shared `Field` appends ` (required)` to it.
- **CI on main was already red before this phase:** mypy failed on 16 errors that had accumulated, and both visual suites failed because only macOS baselines are committed. Both are fixed — mypy is clean, and a first Linux run now writes its baselines and hands them over as an artifact to commit instead of failing.
- **The catalogue is the CSV, and `scripts/load_skus.py` now treats it as one.** It only ever inserted, so a row edited in `data/seeds/skus.csv` kept what it was born with — the four laptop rows never received their `category` — and a row deleted from the CSV stayed for ever, leaving sixteen retired laptops on the shelf. It refreshes a row that exists and retires one the CSV dropped, unless a unit, a serial prefix or a price observation still points at it. The tenant policies hide other organisations' rows from that check, so the delete runs in a savepoint and takes the database's refusal as the answer.
- **`make dev` was showing the old demonstration data rather than the new catalogue.** All sixty-six units sat on pre-category rows, so the window's one filter was "Laptops". `seed_demo_data.py --reset-only` clears the data without reseeding — which is what lets the catalogue be reloaded while nothing references the retired rows — and `--if-missing`, which `dev.sh` now runs, seeds only when there is none, so starting twice never throws away work.
- **A kind can be missing from the window while being fully stocked.** The window shows a unit only while the engine has said to resell it and it has not gone, so a pass in which every unit of a kind was sold, or sent to parts, leaves that kind off the window — which reads exactly like a category nobody added. Kinds with nothing in the window are stocked again with a different seed, up to three times, and any that still have nothing are reported by name instead of passed over.
- **The console listed no units while the shelf was full.** `SKUBase` required `storage_gb` and `ram_gb` to be at least one character long, and twenty catalogue rows have both blank — a hair dryer has neither — so serializing the first such unit raised and the whole list failed with a 500. The two figures are now recorded as the catalogue records them (present for a laptop, blank for a dryer), the console drops a blank figure from a line, and a test covers a unit whose model has no memory figure at all.
- **The application opened in the dark, and the dark was black.** `--background` was `#141311`, a warm near-black, so the first impression of the product was a screen switched off. It opens in light now, the dark theme is re-based on a deep teal ink with a ramp above it, and `tokens.test.ts` fails if any surface in either theme has no hue in it or resolves to black. The two defaults — the inline script in `index.html` and `ThemeProvider` — are read by `theme-default.test.ts` and have to agree, or the first paint flashes the wrong theme.
- **The contrast suite was measuring a copy of itself.** `contrast.test.ts` carried a pasted snapshot of every colour, so a token could be edited in `index.css` and the suite would keep passing against numbers that no longer appeared anywhere on the page. It parses the stylesheet and resolves the pairs by token name now, which is what F9.1 always claimed it did: forty-eight pairs, both themes.
- **Colour meant one hue.** Seven accents and five callout roles existed in both themes and were almost never drawn — every chart, bar and badge was lime, so a reader could not tell two series apart by looking. `src/theme/meaning.ts` is the one place that says what each hue is for, and the analytics panels and the source conditions read from it: regret is a cost in the caution hue, the baseline is a measurement in teal, and a stale source is no longer wearing the yellow that means synthetic data. ADR-008 records the rule and the two things deliberately left outside it.

---

## In Progress

- F11.8 The backdrop and the glass, everywhere — Agent: ai-mimo-ses_e90b81ea6ffe — Started: 2026-10-24T23:11:44Z — Branch: main
- F11.9 The motion — Agent: ai-mimo-ses_e90b81ea6ffe — Started: 2026-10-24T23:11:44Z — Branch: main
- F8.0 Design decision and dependency licences — Agent: ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z — Started: 2026-10-21T00:00:00Z — Branch: feat/F8.0-design-decision-and-licences
- Phase 4/6/7 consolidation — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Started: 2026-10-20T45:45:00Z — Branch: feat/phase5-integration

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
- F4.1 Override with reason — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:57:00Z — Commit: 9b217b0
- F4.2 Outcome logging — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:58:00Z — Commit: 7711b82
- F4.3 Predicted vs realized view — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:59:00Z — Commit: 8617b55
- Phase 5 integration — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T45:30:00Z — Commit: 6fa8cef
- Phase 4/6/7 consolidation — Agent: ai-minimax-m3.1-flash-ses_ea89089b — Completed: 2026-10-20T46:30:00Z — Commit: 3494a26
- F1.1 SKU catalog and seed — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F1.2 Serial prefix lookup — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F1.3 Return intake API — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.4 Inspection record API — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.5 Photo upload — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.6 Intake and inspection UI — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T20:00:00Z
- F1.7 Audit log (model + API) — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T49:00:00Z — Commit: e1d32aa
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
- F4.4 Time-to-sell model — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T18:08:00Z — Commit: 51182d8
- F4.5 Regret calculation — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T18:20:00Z — Commit: 91f49ff
- F4.6 Calibration — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T18:50:00Z — Commit: 974cead
- F4.7 Analytics page — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T19:05:00Z — Commit: 2acccb3
- F4.8 Data export — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T19:20:00Z

---

## Agent Registry

| Agent ID | Type | Assigned Features | Last Active |
|----------|------|-------------------|-------------|
| ai-nemotron-ses_eaa59d66 | AI | F1.1, F1.2, F1.3, F1.4, F1.5, F1.6, F1.7, F3.1, F4.1-F4.8, F5.7, F6.1-F6.9, F7.1-F7.6 | 2026-10-20T52:00:00Z |
| ai-nemotron-ses_eaa6f421 | AI | F0.x, F2.1-F2.11, F3.2-F3.9 | 2026-10-20T12:00:00Z |
| ai-longcat-ses_ea89089b | AI | F4.1, F5.1, F5.2, F5.3, F5.4 | 2026-10-20T22:30:00Z |
| ai-minimax-m3.1-flash-ses_ea89089b | AI | F5.5, F5.6, Phase 5 integration | 2026-10-20T45:00:00Z |
| ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z | AI | F8.0-F8.8 (Phase 8, product surface) | 2026-10-21T00:00:00Z |

---

## License & Data Source Compliance Log

| Date | Action | Source/Library | License | Status |
|------|--------|----------------|---------|--------|
| 2026-10-20 | Added dependency | aiosqlite | MIT | Approved (test dependency) |
| 2026-10-20 | Added dependency | numpy (core dependency for the Monte Carlo engine) | BSD-3-Clause | Approved - already listed in PLAN.md Appendix A |
| 2026-10-20 | Added data source | Synthetic generator (in-house, `ml/synthetic`) | MIT (project license) | Approved - every row tagged `is_synthetic=true` |
| 2026-10-20 | Added data source | Synthetic price source (in-house, log-normal) | MIT (project license) | Approved - `source=synthetic`, `is_synthetic=true` |
| 2026-10-20 | Added dependency | fake-indexeddb (IndexedDB shim for the F5.5 offline store tests) | Apache-2.0 | Approved - dev-only, see ADR-004 |
| 2026-10-21 | Added dependency | @fontsource-variable/inter (self-hosted Inter, replaces the Google Fonts CDN) | SIL OFL 1.1 | Approved - see ADR-006 |
| 2026-10-21 | Added dependency | @fontsource-variable/inconsolata (self-hosted Inconsolata, replaces the Google Fonts CDN) | SIL OFL 1.1 | Approved - see ADR-006 |
| 2026-10-21 | Added dependency | three 0.185.1 (the 3D renderer) | MIT | Approved - see ADR-006. Pinned below 0.186 on purpose: 0.186 removed the shadow map type that react-three-fiber v8 selects by default |
| 2026-10-21 | Added dependency | @react-three/fiber 8.18.0 (the React renderer for three.js) | MIT | Approved - see ADR-006. The React 18 line; v9 needs React 19 |
| 2026-10-21 | Added dependency | @react-three/drei 9.122.0 (helpers for the 3D scene) | MIT | Approved - see ADR-006. Pinned to the version that pairs with fiber v8 |
| 2026-10-21 | Added dependency | @react-three/postprocessing 2.19.1, postprocessing 6.39.5 | MIT, Zlib | Approved - see ADR-006. Reserved for the bloom in F8.8; not yet imported |
| 2026-10-21 | Added dependency | @react-three/test-renderer 8.2.4 (scene-graph assertions) | MIT | Approved - dev-only, see ADR-006 |
| 2026-10-21 | Added dependency | @playwright/test 1.64.1 (the visual regression suite) | Apache-2.0 | Approved - dev-only, already listed in PLAN.md Appendix A |
| 2026-10-21 | Added dependency | @types/node 22.10.2 | MIT | Approved - dev-only, the types for the build and the end-to-end configuration |

---

## ADR Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-001 | Technology Stack Selection | Accepted | 2026-10-20 |
| ADR-002 | Decision Engine Design | Accepted | 2026-10-20 |
| ADR-003 | Market Intelligence Design | Accepted | 2026-10-20 |
| ADR-004 | Offline inspection storage and the fake-indexeddb test shim | Accepted | 2026-10-20 |
| ADR-005 | The feedback loop analytics | Accepted | 2026-10-20 |
| ADR-006 | The design system and the spatial decision console | Accepted | 2026-10-21 |
| ADR-007 | The shop window is a separate application | Accepted | 2026-10-21 |

---

*Last updated: 2026-10-21*
*Next review: Phase 10 is complete. The engine is not changed by it. The two open
questions are the login that nothing authenticates yet, and the basket the shop
window does not have.*
