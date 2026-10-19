# PROGRESS.md — SecondRoute Build Tracker

> **Single source of truth for project status.** Updated by every agent on every change.

---

## Current Phase: **Phase 1 — Unit Intake and Inspection Record** (F1.1-F1.5 complete, F1.6-F1.7 remaining)

**Target:** Digital return log with inspections and photos.

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
| F1.6 Intake and inspection UI | 🔲 Not Started | — | — | — | — | — | New return, inspection form, unit detail, draft save |
| F1.7 Audit log | 🔲 Not Started | — | — | — | — | — | Every mutation writes audit_log, immutable |

**Phase 1 Exit Criteria:** Warehouse can run returns through SecondRoute as digital log. Every inspection recorded and queryable.

---

## Phase 2: Decision Engine v0 (Synthetic-Backed)

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F2.1 Synthetic returns generator | 🔲 Not Started | — | — | — | — | — | Seeded, realistic distributions, `is_synthetic=true` |
| F2.2 Price source interface | 🔲 Not Started | — | — | — | — | — | `PriceSource` protocol, synthetic impl, `price_observations` table |
| F2.3 Grade rules | 🔲 Not Started | — | — | — | — | — | Inspection → grade distribution (A/B/C/D), monotonicity |
| F2.4 Cost tables | 🔲 Not Started | — | — | — | — | — | Fees, logistics, handling, repair defaults, admin API |
| F2.5 Channel evaluator (Monte Carlo) | 🔲 Not Started | — | — | — | — | — | 10k draws, net p10/p50/p90, seeded RNG |
| F2.6 Risk profile and utility | 🔲 Not Started | — | — | — | — | — | Conservative/balanced/aggressive, certainty equivalent |
| F2.7 Confidence gating and SAFE_DEFAULT | 🔲 Not Started | — | — | — | — | — | P(best within 5%) ≥ 0.70, else SAFE_DEFAULT (highest p10) |
| F2.8 Reasons and flip conditions | 🔲 Not Started | — | — | — | — | — | Top contributors, one-at-a-time sensitivity |
| F2.9 Decision API and persistence | 🔲 Not Started | — | — | — | — | — | POST/GET decisions, input_snapshot_hash |
| F2.10 Action card templates | 🔲 Not Started | — | — | — | — | — | Per-channel steps, NIST 800-88 wipe, no LLM |
| F2.11 Decision card UI | 🔲 Not Started | — | — | — | — | — | Channel, confidence, net range, reasons, flip, badge |

**Phase 2 Exit Criteria:** End-to-end demo. Inspect MacBook fixture → card with range + flip condition. Repeatable. Labeled prototype.

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
| F4.1 Override with reason | 🔲 Not Started | — | — | — | — | — | POST /decisions/{id}/override, required reason, UI dialog |
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
| F5.5 Offline inspection | 🔲 Not Started | — | — | — | — | — | IndexedDB drafts, queue sync, conflict resolution |
| F5.6 Historical backtest | 🔲 Not Started | — | — | — | — | — | No look-ahead, baseline comparison, bootstrap CI |
| F5.7 Explanation text (optional) | 🔲 Not Started | — | — | — | — | — | Ollama + open-weights, validator, fallback to template |
| F5.8 Staging deployment and backups | 🔲 Not Started | — | — | — | — | — | Compose on Linux VM, Caddy TLS, pg_dump + restic |

**Phase 5 Exit Criteria:** Pilot-ready. Login, org isolation, offline, batches, backtest result.

---

## Phase 6: Learning Loop

| Feature | Status | Owner | Branch | Started | Completed | Commit | Notes |
|---------|--------|-------|--------|---------|-----------|--------|-------|
| F6.1 Model registry | 🔲 Not Started | — | — | — | — | — | MLflow, training data hash, metrics, calibration, features |
| F6.2 Shadow mode | 🔲 Not Started | — | — | — | — | — | Candidate runs alongside, logs only, never shown to users |
| F6.3 Promotion gate | 🔲 Not Started | — | — | — | — | — | Beats active on net MAE + ECE, min sample, admin action |
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

- F1.6 — Agent: ai-nemotron-ses_eaa59d66 — Started: 2026-10-20T18:00:00Z — Branch: feat/F1.6-intake-ui
- F1.7 — Agent: ai-nemotron-ses_eaa59d66 — Started: 2026-10-20T18:00:00Z — Branch: feat/F1.7-audit-log

---

## Blocked

*No features currently blocked.*

---

## Done

- F1.1 SKU catalog and seed — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F1.2 Serial prefix lookup — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T16:45:00Z
- F1.3 Return intake API — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.4 Inspection record API — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z
- F1.5 Photo upload — Agent: ai-nemotron-ses_eaa59d66 — Completed: 2026-10-20T17:45:00Z

---

## Agent Registry

| Agent ID | Type | Assigned Features | Last Active |
|----------|------|-------------------|-------------|
| ai-nemotron-ses_eaa59d66 | AI | F1.1, F1.2, F1.3, F1.4, F1.5, F1.6, F1.7 | 2026-10-20T17:45:00Z |
| ai-nemotron-ses_eaa6f421 | AI | F0.1, F0.2, F0.3, F0.4, F0.5, F0.6, F0.7 | 2026-10-20T03:30:00Z |

---

## License & Data Source Compliance Log

| Date | Action | Source/Library | License | Status |
|------|--------|----------------|---------|--------|
| 2026-10-20 | Added dependency | aiosqlite | MIT | Approved (test dependency) |

---

## ADR Log

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| — | — | — | — |

---

*Last updated: 2026-10-20*
*Next review: Before starting Phase 2 work*