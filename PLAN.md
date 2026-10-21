# SecondRoute: Phased Build Plan

> One return in. One disposition instruction out.

This plan splits SecondRoute into **8 phases** (0 to 7). Each phase is an independently buildable, demoable increment with its own exit criteria. Each phase is broken into **features** (IDs like `F2.5`), where a feature is the smallest unit worth merging on its own.

**Hard constraint:** every tool, library, dataset, and service is free and open source, or has a free tier we can run without payment. Licenses are listed in Appendix D.

---

## How to read this plan

- **Phase:** a shippable increment. It has a goal, a `Requires` line, a list of features, and an exit demo.
- **Feature:** one piece of work with acceptance criteria. Acceptance criteria are the definition of done.
- **Independence:** each phase works on its own once its `Requires` phases are done. Nothing in a phase should need work from a later phase.
- **Synthetic first:** Phases 2 and 4 run entirely on synthetic or self-generated data. Real free data arrives in Phase 3 and replaces the synthetic adapters without changing decision code. Partner data arrives in Phase 5. No phase before Phase 5 blocks on a partner.
- **Stop points:** each phase ends with a point where the product is useful even if later phases never happen.

### Phase map

| Phase | Name | Requires | Delivers | Useful on its own as |
|---|---|---|---|---|
| 0 | Foundation | none | Repo, stack, CI, walking skeleton | Dev base |
| 1 | Unit intake and inspection record | 0 | Digital return log with inspections and photos | Replaces paper and spreadsheets |
| 2 | Decision engine v0 | 1 | Recommendation card on synthetic prices | Demo of the core idea |
| 3 | Market, cost, and component intelligence | 2 | Real free price, component, and demand signals | Better numbers, same product |
| 4 | Feedback loop and analytics | 2 | Outcomes, overrides, regret, calibration | Measures its own accuracy |
| 5 | Pilot readiness | 4 (3 optional) | Auth, tenancy, batch, offline, backtest, staging | Design partner pilot |
| 6 | Learning loop | 5 | Shadow models, exploration, photo assist | Model improves from outcomes |
| 7 | Ecosystem and expansion | 6 | Second category, fraud signals, partner APIs | Product line expansion |
| 8 | Product surface | 2, 4 | One design system, one spatial decision console | A surface worth using |
| 9 | Colours, cache and data | 8 | Measured contrast, real data, closed defects | An application worth using |

**Note on Phase 3:** it is optional for Phase 4 and Phase 5. Phase 5 can start with synthetic prices if the partner shares sold data directly, but Phase 3 is strongly recommended before any pilot that makes money claims.

---

## Principles (apply to every phase)

1. **Decisions are explainable.** Every recommendation shows channel, confidence, net range, top reasons, and the flip condition.
2. **Uncertainty is first-class.** Prices are distributions (p10, p50, p90). Low confidence returns `SAFE_DEFAULT`.
3. **The LLM writes words, not decisions.** Channel choice and valuation are deterministic code and statistical models.
4. **Log everything from Phase 1.** Missing logs cannot be backfilled, and the outcome data is the moat.
5. **Respect licenses and ToS.** Official APIs, public datasets, and partner data only. No scraping that violates terms.
6. **Every number has a source and an as-of date.** Shown in the UI.

---

## Phase 0: Foundation

**Goal:** a repo where any developer can run the full stack, tests pass, and CI is green.
**Requires:** none.

### F0.1 Repository and license
- Create the repo with MIT or Apache-2.0 license, README, `.gitignore`, and this PLAN.md.
- Add an ADR (architecture decision record) template in `docs/decisions/`.
- **Accept:** clone, read README, see license file. ADR template exists.

### F0.2 Docker Compose stack
- Services: PostgreSQL 16, Redis, Caddy. Other services are added in later phases.
- **Accept:** `docker compose up` brings all services to healthy status. Postgres accepts connections from the backend container.

### F0.3 Backend skeleton
- FastAPI app with config loading (env vars), structured logging, `/health` endpoint, and a `core/` package for db and config.
- Tooling: ruff, mypy, pytest, pytest-cov.
- **Accept:** `GET /health` returns 200 with DB status. One sample test passes. `ruff` and `mypy` pass.

### F0.4 Frontend skeleton
- Vite, React 18, TypeScript, Tailwind, shadcn/ui, TanStack Query, React Router.
- A home page that calls `/health` and displays the result.
- **Accept:** page renders, shows backend status, Vitest runs one test.

### F0.5 Migration baseline
- Alembic initialized. Empty baseline migration. Migration command documented in README.
- **Accept:** `alembic upgrade head` and `downgrade base` both succeed.

### F0.6 CI pipeline
- GitHub Actions: lint, typecheck, unit tests for backend and frontend, compose smoke test.
- **Accept:** a PR with a failing test is blocked. A passing PR shows green.

### F0.7 Data-source register
- Create `docs/data-sources.md` with a table: source, purpose, license, access method, rate limits, retrieval log.
- **Accept:** file exists and lists every source from Appendix D, each with a status.

**Phase 0 exit:** walking skeleton runs end to end in Compose, CI is green, and the team can add features without setup friction.

---

## Phase 1: Unit intake and inspection record

**Goal:** inspectors can log every returned unit, its inspection, and its photos. The data is captured from day one, even before any intelligence exists.
**Requires:** Phase 0.

### F1.1 SKU catalog and seed
- `skus` table (family, model name, year, storage, RAM, color, region, specs JSON, source, as-of date).
- Seed CSV of 10 to 20 laptop SKUs with source and as-of columns. Curated manually from public manufacturer specs.
- **Accept:** seed loader is idempotent (running twice changes nothing). Every row has a source and as-of date.

### F1.2 Serial prefix lookup
- `serial_prefixes` table and `GET /api/v1/skus/lookup?serial=...`.
- Known prefix returns SKU. Unknown prefix returns 404 with `manual_selection_required`.
- **Accept:** test with known, unknown, and malformed serials.

### F1.3 Return intake API
- `POST /api/v1/units` with SKU, serial (optional), return reason code (enum), order channel.
- Status set to `received`.
- **Accept:** invalid reason code returns 422. Created unit can be fetched by ID.

### F1.4 Inspection record API
- `POST /api/v1/units/{id}/inspections` with battery health, battery cycles, cosmetic grade, functional tests (JSON), accessories checklist (JSON), activation lock flag, notes.
- Append-only. Multiple inspections allowed, latest one is current. Status moves to `inspected`.
- **Accept:** battery health outside 0 to 100 is rejected. Second inspection does not overwrite the first.

### F1.5 Photo upload
- Upload endpoint stores files on local volume (SeaweedFS later). Max size and allowed types enforced. EXIF metadata stripped, including GPS.
- **Accept:** test image with GPS EXIF comes back with no GPS fields. Oversized file returns 413.

### F1.6 Intake and inspection UI
- Pages: new return intake, inspection form, unit detail (history of inspections and photos).
- Basic draft save in browser state so a page reload does not lose input.
- **Accept:** a tester can log one full return, with three photos, in under 3 minutes on desktop.

### F1.7 Audit log
- Every create and update writes a row to `audit_log` with actor (anonymous until Phase 5), entity, action, and payload.
- **Accept:** each mutation produces exactly one audit row. Audit rows cannot be edited via the API.

**Phase 1 exit:** a warehouse can run its returns through SecondRoute as a digital log. Every inspection is recorded and queryable.

---

## Phase 2: Decision engine v0 (synthetic-backed)

**Goal:** every inspected unit gets a recommendation card: channel, confidence, net range, reasons, and flip conditions. Prices are synthetic, so this phase is a prototype of the decision logic.
**Requires:** Phase 1.

### F2.1 Synthetic returns generator
- Generates units with realistic grade distributions, battery cycles, accessory loss rates, and return reasons. Every generated row has `is_synthetic = true`.
- Seeded, so the same seed gives the same dataset.
- **Accept:** same seed, same output (hash test). Distributions documented in `ml/synthetic/README.md`.

### F2.2 Price source interface
- `PriceSource` protocol with `get_distribution(sku, grade, channel, as_of)`.
- `price_observations` table. Synthetic implementation of the protocol.
- **Accept:** two fake implementations with different outputs can be swapped in tests, and the decision code is unchanged.

### F2.3 Grade rules
- Maps inspection fields to a probability distribution over grades A, B, C, D. Starts with explicit rules (battery health thresholds, cosmetic grade, functional test failures).
- **Accept:** probabilities sum to 1. Worse battery health never increases the probability of grade A (monotonicity test).

### F2.4 Cost tables
- `cost_tables` table for fees, logistics, handling, and repair defaults. Each row has source and as-of date.
- Admin API to read and update values.
- **Accept:** no cost value can be saved without a source field.

### F2.5 Channel evaluator (Monte Carlo)
- For each eligible channel, samples 10,000 draws from the sale price, fee, repair, logistics, and holding distributions. Computes net p10, p50, p90, and P(this channel is best).
- Seeded RNG.
- **Accept:** same seed, same result. Net value decreases as fees increase (property test using hypothesis).

### F2.6 Risk profile and utility
- Three profiles: conservative, balanced, aggressive. Ranking uses certainty equivalent `mean − λ × stddev`, with λ set per profile in config.
- **Accept:** on a fixture where two channels have close means and one has much higher variance, the conservative profile picks the lower-variance channel and the aggressive profile picks the higher-mean one.

### F2.7 Confidence gating and SAFE_DEFAULT
- Confidence is P(recommended channel is within 5% of the best net). Default threshold 0.70.
- Below threshold, return `SAFE_DEFAULT` (the channel with the highest p10) with the reason.
- **Accept:** a fixture with overlapping distributions returns `SAFE_DEFAULT`. A fixture with a clear winner returns the winner.

### F2.8 Reasons and flip conditions
- Top reasons: the largest contributors to the difference between the top two channels.
- Flip conditions: one-at-a-time sensitivity. For each input, find the value that changes the recommendation, and report it in plain language.
- **Accept:** each flip condition names one input and a threshold. Test with a fixture where changing one input flips the decision.

### F2.9 Decision API and persistence
- `POST /api/v1/units/{id}/decide` runs the engine and stores the decision with `input_snapshot_hash`.
- `GET /api/v1/decisions/{id}` returns full output.
- **Accept:** identical inputs produce identical output and hash. A decision can be reproduced from its stored snapshot.

### F2.10 Action card templates
- Action steps per channel from templates (for example, resell open-box: wipe per NIST 800-88, photograph four angles, attach label). No LLM in this phase.
- **Accept:** every channel in the decision space has a template. A decision with `SAFE_DEFAULT` shows a human-inspection step.

### F2.11 Decision card UI
- Shows channel, confidence bar, net range, alternatives with deltas, reasons, flip conditions, action steps, and a "prototype, synthetic prices" badge.
- Buttons: Accept only. Override comes in Phase 4.
- **Accept:** renders correctly for three fixtures: a clear winner, a `SAFE_DEFAULT` case, and a case with a flip condition.

**Phase 2 exit:** end-to-end demo. Inspect a MacBook fixture, get a card with a range and a flip condition, and see the same result when the test is repeated. Clearly labeled prototype.

---

## Phase 3: Market, cost, and component intelligence

**Goal:** replace synthetic prices with free and open data where it exists, and add component and demand signals. Decision code does not change; only adapters and data do.
**Requires:** Phase 2.

### F3.1 eBay Browse API adapter
- Fetches active listings for SKU keywords using a free developer key. Maps listing condition to our grades.
- Stored as `price_observations` with `source = ebay_active`.
- Handles rate limits with backoff and caches responses.
- **Accept:** rate-limit response triggers retry. Stored rows carry the source tag. Attribution text appears in the UI where prices are shown.

### F3.2 Partner sold-data CSV import
- `POST /api/v1/imports/sales` with a column mapping step, validation, and a dry-run mode that reports rejected rows with reasons.
- Idempotent: the same file imported twice adds no duplicates (file hash check).
- **Accept:** dry-run returns the same row counts as the real import. Re-importing the same file changes nothing.

### F3.3 Price cleaning
- MAD-based outlier removal, grade normalization, recency weighting with exponential decay (half-life configurable, default 30 days).
- **Accept:** injected outliers are removed. Weight of a 60-day-old observation is about a quarter of a fresh one at a 30-day half-life.

### F3.4 Price quantile model
- LightGBM quantile regression for p10, p50, p90 per SKU family and grade.
- Fallback to empirical quantiles when the sample is below a minimum (default 30).
- **Accept:** pinball loss is logged per model version. Fallback triggers below the sample threshold (test).

### F3.5 Component prices and FRED adapter
- `component_prices` table (component type, price per unit, source, as-of, confidence weight).
- Scheduled job pulls configured FRED series (free API key). Series IDs are set in config and verified when implemented.
- Manual entry and partner CSV for component prices.
- **Accept:** a component price older than its freshness limit is flagged stale in the API response.

### F3.6 Parts harvest valuation
- Per-unit parts value = sum of recoverable components × yield assumption − labor. Inputs from `component_prices` and a teardown yield table.
- Adds `PARTS_HARVEST` to the channel evaluator with its own distribution.
- **Accept:** a unit with a failed display shows lower parts value than an intact one (test). Card shows the component source and as-of date.

### F3.7 Demand signal (Wikimedia Pageviews)
- Weekly pageview counts for product articles mapped to SKU families. Free API, no key, User-Agent set, cached.
- Stored as a demand feature. Not yet applied to price in this phase; it is available for the model.
- **Accept:** 429 responses back off. Weekly series is stored with the query parameters used.

### F3.8 Launch calendar and HOLD logic
- `launch_events` table (manually curated from public announcements, each with a source URL).
- `decay_params` per SKU family and grade, fit from price observations over time.
- HOLD is only offered when expected change over the hold window is positive at p50 and the probability of a launch inside the window is below threshold.
- **Accept:** HOLD is not offered for a unit one day before a known launch event (test). HOLD is offered for a fixture with a rising price and no launch in the window.

### F3.9 Source health and confidence downgrade
- `GET /api/v1/sources/health` lists each source with last update, freshness status, and error count.
- A stale source reduces confidence by a configured factor and adds a warning to the card.
- **Accept:** disabling a source in a test lowers confidence and adds a warning in the decision response.

**Phase 3 exit:** prices, components, and demand come from free or partner sources, each shown with its source and as-of date. The decision engine code is unchanged from Phase 2.

---

## Phase 4: Feedback loop and analytics

**Goal:** record what actually happened, compare it to predictions, and measure the system's accuracy and regret. This is where the data moat starts to compound.
**Requires:** Phase 2. Phase 3 improves quality but is not required.

### F4.1 Override with reason
- `POST /api/v1/decisions/{id}/override` with chosen channel and required reason text.
- UI: override dialog on the decision card. Reason is required.
- **Accept:** override without reason returns 422. Overrides are stored and appear on the unit history.

### F4.2 Outcome logging
- `POST /api/v1/units/{id}/outcome` with channel taken, sale price, actual fees, actual repair cost, actual logistics, days to disposition, final status.
- Append-only, linked to the decision that was active at the time.
- **Accept:** outcome for a unit with no decision is rejected. Second outcome creates a new row, does not overwrite.

### F4.3 Predicted vs realized view
- Per unit: predicted net (p10, p50, p90) against realized net, with the residual and whether the realized value fell inside the range.
- **Accept:** residual and in-range flag are correct on fixtures (test).

### F4.4 Time-to-sell model
- Kaplan-Meier curves of days-to-sell by channel and grade, computed from outcomes. Cox model added later.
- Falls back to the prior from Phase 3 when the sample is below a minimum.
- **Accept:** curve matches a hand-computed example. Fallback triggers below the minimum (test).

### F4.5 Regret calculation
- Regret = best realized net among tested channels − realized net of chosen channel.
- When only one channel was observed, regret is estimated from the model and labeled `estimated`.
- **Accept:** observed and estimated regret are stored with different flags and never summed without labeling.

### F4.6 Calibration
- Reliability curve (predicted vs observed best-channel frequency), ECE, and an isotonic recalibration step.
- Recalibration is a versioned step, not applied silently.
- **Accept:** ECE matches a reference implementation on a fixture. Recalibration version is stored with decisions.

### F4.7 Analytics page
- North star (net recovered value per return, above baseline), regret over time, calibration plot, override rate by reason.
- Synthetic and real data are displayed separately, never merged silently.
- **Accept:** all charts render with fixtures. A synthetic-only dataset shows the synthetic badge.

### F4.8 Data export
- CSV export of decisions, overrides, and outcomes, including snapshot hashes and model versions.
- **Accept:** export round-trips: re-importing the export reproduces the same row counts and hashes.

**Phase 4 exit:** the system measures its own accuracy and decision quality. The first calibration and regret numbers exist, even on synthetic data.

---

## Phase 5: Pilot readiness

**Goal:** a design partner can use SecondRoute safely with real users, real data, and real backups.
**Requires:** Phase 4. Phase 3 strongly recommended.

### F5.1 Authentication
- Keycloak in Compose. OIDC login in the frontend. Roles: inspector, manager, admin, analyst.
- Role checks on every endpoint.
- **Accept:** an inspector cannot call admin endpoints (403). Unauthenticated calls return 401.

### F5.2 Tenant isolation
- `org_id` on every table. PostgreSQL row-level security enforces isolation.
- **Accept:** a test user in org A cannot read or write org B records through any endpoint, including batch and export.

### F5.3 Risk profile settings
- UI and API to set the retailer's risk profile. Changing it recomputes decisions on the next request, and the change is audited.
- **Accept:** a fixture where the profile flips the recommendation shows the change after update.

### F5.4 Batch decisions
- `POST /api/v1/batches/decide` for many units. Batch view grouped by channel, filterable by value, confidence, and deadline. CSV export.
- **Accept:** a 500-unit batch completes within the configured time budget. Grouping counts match unit counts.

### F5.5 Offline inspection
- Inspection drafts stored in IndexedDB. Submissions queue while offline and sync on reconnect.
- Conflicts resolved by last write, and both versions are kept in the audit log.
- **Accept:** a full inspection completed offline syncs correctly when the network returns. No data lost in a forced-disconnect test.

### F5.6 Historical backtest
- Replays past returns using only data available at each decision time (no look-ahead). Compares the engine against the partner's baseline policy. Reports net difference with a bootstrap confidence interval.
- **Accept:** a test fails the build if any feature for a decision uses data timestamped after the decision time. Report includes the interval, not only the point estimate.

### F5.7 Explanation text (optional)
- Ollama runs an open-weights model with a commercially usable license (verify model card at deploy time). Input is structured decision JSON only.
- Validator rejects any output containing a number that is not in the input. Failing output falls back to the Phase 2 template.
- **Accept:** on a test set of 100 decisions, every output either passes the validator or uses the template. No unseen numbers reach the UI.

### F5.8 Staging deployment and backups
- Compose stack on a Linux VM with Caddy for TLS. Daily `pg_dump` and `restic` backups to a second location.
- Restore drill documented in `docs/runbooks/restore.md`.
- **Accept:** a restore into a fresh environment reproduces row counts and passes the smoke test.

**Phase 5 exit:** pilot-ready. Users log in, see only their org's data, work offline, run batches, and the team has a backtest result to show.

---

## Phase 6: Learning loop

**Goal:** the model improves from outcomes in a controlled, auditable way.
**Requires:** Phase 5, with enough real outcomes to evaluate a new model (set the minimum in the pilot plan).

### F6.1 Model registry
- MLflow tracks each model version with training data hash, metrics, calibration curve, and feature list.
- **Accept:** every decision stores the model version. A registered model can be loaded and reproduces its own metrics.

### F6.2 Shadow mode
- A candidate model runs alongside the active one, logs predictions, and does not affect what users see.
- **Accept:** shadow predictions are stored for every decision. Users never see shadow output (test).

### F6.3 Promotion gate
- Promotion requires the shadow model to beat the active model on held-out outcomes for net MAE and calibration ECE, with a minimum sample.
- Promotion is a recorded, audited action by an admin.
- **Accept:** a candidate that is worse on either metric is blocked from promotion (test).

### F6.4 Drift monitoring
- Population stability index on inputs, calibration drift on outputs, exported to Prometheus and shown in Grafana with alert rules.
- **Accept:** an injected input shift triggers the alert in a test environment.

### F6.5 Controlled exploration
- For a capped share of units (default 3 to 5%), the system may recommend the second-best channel. Eligibility excludes high-value units and conservative-profile retailers.
- Propensity of each choice is logged.
- **Accept:** no exploration on excluded units (test). Propensity is stored for every explored decision.

### F6.6 Thompson sampling over channels
- Bandit policy using NumPy, operating only within exploration-eligible units.
- **Accept:** on a simulated environment with known channel values, regret decreases over time compared to random choice.

### F6.7 Off-policy evaluation
- Inverse propensity scoring to estimate the value of a proposed policy from logged decisions, with confidence intervals.
- **Accept:** on a simulated log, the estimate matches the known true value within the reported interval.

### F6.8 Photo condition assist
- OpenCV checks photo quality (blur, lighting). An open-license classifier suggests screen and body damage. Tesseract or PaddleOCR reads serial labels.
- Suggested grade changes are bounded (for example, at most one grade) and always require inspector confirmation.
- **Accept:** a suggestion outside the bound is rejected. Every suggestion is stored alongside the inspector's final grade.
- **License gate:** a model is only used if its license is on the allowed list in `docs/data-sources.md`.

### F6.9 Monthly expert review
- Workflow that samples 30 random decisions per category for expert review. Reviewer labels agreement and reason. Labels are stored and can feed training.
- **Accept:** sample is reproducible from a seed. Labels link to the decision IDs.

**Phase 6 exit:** a new model has been promoted from shadow based on measured outcomes, with an audit trail.

---

## Phase 7: Ecosystem and expansion

**Goal:** expand beyond laptops and add the value propositions that come from having outcome data.
**Requires:** Phase 6.

### F7.1 Second category onboarding
- Adding a new SKU family (phones or tablets) needs only configuration, seed data, and cost tables. No code changes in the decision engine.
- **Accept:** a test family added by config alone produces a decision card.

### F7.2 Lot and batch optimization
- Groups units by destination (liquidator lot, refurb batch, shipment) to optimize shipping and lot discounts.
- **Accept:** grouping reduces total logistics cost versus per-unit baseline on a fixture.

### F7.3 Fraud and wardrobing signals
- Flags for serial mismatch, component swap (for example, serial-to-component mismatch), and activation lock mismatch.
- Flags go to a review queue. They never auto-reject a return.
- **Accept:** each flag type has a fixture that triggers it and a fixture that does not.

### F7.4 Upstream return-reason insights
- Report of return reasons and rates by SKU family, for product and listing teams.
- **Accept:** report reproduces counts from the raw unit table.

### F7.5 Partner integrations via open APIs
- Adapter pattern for partner systems (liquidator bid APIs, retailer order systems) under written agreements.
- **Accept:** a new adapter can be added without changing the decision package. Adapter has contract tests.

### F7.6 Data ownership tools
- Export and delete tools per tenant, including data deletion at contract end, with audit records.
- **Accept:** a tenant deletion removes all rows for that org and leaves an audit record of the deletion.

**Phase 7 exit:** a second category runs on the same engine, and at least one outcome-data insight is shipped to a customer.

---

## Phase 8: Product surface

**Goal:** one design system and one decision surface, so the product reads as a single instrument rather than nine screens assembled one at a time.

**Requires:** Phase 2 and Phase 4. Phases 5, 6 and 7 are unaffected.

**Why this phase exists:** every phase before it was about the engine. The engine works, the data is real, and the surface that presents it does not. The operator's most important question — *how much do these channels overlap?* — is answered with a percentage. This phase makes the overlap visible, and makes every other surface consistent with it.

### F8.0 Design decision and dependency licences
- ADR-006 records the design language, the spatial decision console, and every new dependency with its licence.
- PLAN.md Appendix A and D carry the new entries. `CHANGELOG.md` exists and follows Keep a Changelog.
- **Accept:** ADR-006 is accepted; every new dependency has a licence recorded in the compliance log before it is installed.

### F8.1 Design tokens, theme and self-hosted fonts
- The pmndrs MD3 token set as CSS custom properties, in both light and dark, expressed as colour channels so opacity modifiers work.
- The Tailwind scale carries the pmndrs radii, the brand accents, the callout roles, the elevation model and the single transition curve.
- A theme provider with light, dark and system modes, persisted, applied before first paint so the page never flashes.
- Inter and Inconsolata ship as packages. No font is fetched from a third party at runtime.
- **Accept:** the application renders identically with and without the network; the theme survives a reload without a flash; no request leaves the origin for a font.

### F8.2 The interface kit
- One primitive per recurring idea: button, card, badge, callout, tabs, table, field, radio cards, checkbox group, meter, range bar, dialog, sheet, skeleton, tooltip, empty state, keyboard key, scroll fade, code block.
- Every primitive carries the pmndrs treatment: the radius scale, the hairline ring, the 26px button, the 20px badge lozenge, the tinted callout.
- **Accept:** the five hand-rolled alert banners in the current application are replaced by one callout with five tones; no page carries a bespoke banner.

### F8.3 The application shell
- A 288px sidebar that collapses to a 48px rail, with the active item as a lime half-pill hugging the content edge.
- A sticky glass header with a search trigger, a keyboard hint and the theme toggle.
- A command palette that navigates, runs a decision and toggles the theme from the keyboard.
- The offline queue state is visible in the shell, not only on the inspection form.
- **Accept:** every destination is reachable by mouse and by keyboard; the shell is usable at 360px wide.

### F8.4 The decision distribution endpoint
- `GET /api/v1/decisions/{id}/distribution` replays the stored decision from its input snapshot and returns the binned density of the engine's own Monte Carlo draws, per channel, on a shared axis.
- The response carries the input snapshot hash.
- **Accept:** the same decision always returns the same histogram; the histogram is derived from the samples and not from a fitted curve.

### F8.5 The channel landscape and the decision card
- The landscape is built first as a two-dimensional SVG ridgeline: accessible, printable, and testable without a GPU.
- A react-three-fiber scene is layered on top of the same data behind a lazy boundary, with a WebGL support probe and a fallback to the two-dimensional view.
- The decision card is rebuilt around the landscape: the recommendation, the confidence, the net range, the alternatives, the reasons, the flip conditions, the action steps and the provenance.
- **Accept:** the three-dimensional view never renders a blank rectangle; with WebGL disabled the operator sees the same data; the existing decision card tests still pass.

### F8.6 Intake, inspection and unit surfaces
- The intake and inspection forms become stepped forms with the counter-based step markers, radio cards and a sticky action bar.
- The unit list gains a filter rail and a table with the scroll-driven edge fade.
- The unit detail becomes tabbed, and the photographs render.
- **Accept:** a tester logs a full return with three photographs in under three minutes; an inspection completed offline still syncs.

### F8.7 Dashboard, health, analytics and backtest surfaces
- The dashboard shows the north star, the live system state and working quick actions.
- The analytics page uses real charts. The synthetic and the real data stay in separate panels.
- The backtest page shows the interval band and the look-ahead verdict as a callout.
- **Accept:** every chart renders with the fixtures; a synthetic-only dataset shows the synthetic badge.

### F8.8 Motion, accessibility and the visual regression suite
- Scroll-driven edge fades on the wide surfaces, shimmer on the loading states, and `prefers-reduced-motion` respected throughout.
- A focus-trap audit, a keyboard pass, and a text alternative for every canvas.
- A Playwright visual regression suite over the critical routes in both themes.
- **Accept:** the whole application is navigable by keyboard alone; the reduced-motion preference disables the non-essential motion.

**Phase 8 exit:** the application has one design system, one decision console, and a test suite that proves both.

---

## Phase 9: The colours, the cache and the data

**Goal:** the interface reads, the application has something in it, and the defects that Phase 8 uncovered are closed.

**Requires:** Phase 8.

**Why this phase exists:** Phase 8 rebuilt the surface. Looking at it with real data in it, and with the colour pairs measured rather than eyeballed, turned up more than the rebuild had fixed.

### F9.1 The colour grading
- Every pair of colours the interface draws is measured against the 4.5 to one that body text needs and the 3 to one that the boundary of a control needs.
- The badges follow the Material Design 3 pattern: the brand tone is the background and the tone that belongs on it is the text.
- The boundary of a control is separated from the hairline between two panels, because a divider is decoration and does not have to be read.

**Accept:** every pair passes; a pair that fails is a failing test.

### F9.2 The cache
- The dependency that was reported as unreachable is installed, running, and reported correctly.
- A dependency that is not configured is not a failure, and is not called a queue.

**Accept:** the service reports itself healthy, and a machine with no cache is not degraded for the want of one.

### F9.3 The photographs and the data
- There is a way to put a photograph in, and the photograph is written out again from its pixels so that nothing about the camera, the moment or the place survives in it.
- There is a workload to look at: units, inspections, photographs, the decisions the engine made, the overrides and the outcomes.

**Accept:** a photograph that carries a camera, a moment and a place comes out with none of them, and the application has a workload in it.

### F9.4 The defects
- The isolation binds on every table that has a policy.
- The offline path works on a machine that is not a secure context, and a rejected entry is not sent for ever.
- The two dialogs trap the focus and give it back.
- A failure is never shown as a number of zero.

**Accept:** every defect has a test that fails without the fix.

**Phase 9 exit:** the colours are measured, the cache is up, there is data and there are photographs, and the defects are closed.

---

## Appendix A: Technology stack

| Layer | Choice | License |
|---|---|---|
| Backend language | Python 3.12 | PSF |
| API | FastAPI, Pydantic v2 | MIT |
| ORM and migrations | SQLAlchemy 2.x, Alembic | MIT |
| Database | PostgreSQL 16 | PostgreSQL License |
| Analytics | DuckDB, Parquet | MIT, Apache-2.0 |
| Pipelines | Prefect (OSS server) | Apache-2.0 |
| Jobs | Redis, RQ | BSD, MIT |
| Scraping (only where permitted) | Scrapy | BSD |
| Browser tests | Playwright | Apache-2.0 |
| ML | scikit-learn, LightGBM, statsmodels, NumPy | BSD, MIT |
| Experiment registry | MLflow | Apache-2.0 |
| Computer vision | OpenCV, Tesseract or PaddleOCR | Apache-2.0 |
| Explanation LLM runtime | Ollama | MIT |
| Frontend | React 18, Vite, TypeScript, Tailwind, shadcn/ui, TanStack Query, Recharts | MIT |
| Design system | pmndrs MD3 tokens (lime seed), Tailwind, self-hosted Inter and Inconsolata | MIT, SIL OFL 1.1 |
| 3D decision console | three, @react-three/fiber v8, @react-three/drei v9, @react-three/postprocessing | MIT (postprocessing: Zlib) |
| Offline storage | IndexedDB (browser), `idb` library | MIT |
| Auth | Keycloak | Apache-2.0 |
| Reverse proxy, TLS | Caddy | Apache-2.0 |
| Containers | Docker, Docker Compose | Apache-2.0 |
| Photo storage | Local volume (dev), SeaweedFS (prod) | Apache-2.0 |
| Metrics, dashboards | Prometheus, Grafana | Apache-2.0, AGPL-3.0 |
| Logs | Loki | AGPL-3.0 |
| Tracing | OpenTelemetry | Apache-2.0 |
| Tests | pytest, hypothesis, schemathesis, Vitest, Playwright | MIT, Apache-2.0 |
| 3D test renderer | @react-three/test-renderer v8 | MIT |
| Lint, types | ruff, mypy, eslint | MIT |
| CI | GitHub Actions | Service terms |
| Secrets in repo (if needed) | SOPS | MPL-2.0 |
| Backups | pg_dump, restic | PostgreSQL License, BSD-2 |

---

## Appendix B: Core data model

```
organizations(id, name, risk_profile, created_at)
users(id, org_id, email, role)
skus(id, family, model_name, year, storage_gb, ram_gb, color, region, specs_json, source, as_of)
serial_prefixes(prefix, sku_id, source, as_of)
units(id, org_id, sku_id, serial, received_at, return_reason_code, order_channel, status)
inspections(id, unit_id, inspector_id, created_at, battery_health_pct, battery_cycles,
            cosmetic_grade, functional_tests_json, activation_lock, accessories_json, notes)
photos(id, unit_id, inspection_id, storage_path, exif_stripped, created_at)
condition_estimates(id, unit_id, grade_dist_json, model_version, created_at)
price_observations(id, sku_id, grade, channel, price, currency, source, observed_at, weight, is_synthetic)
component_prices(id, component_type, price_per_unit, unit, source, as_of, confidence_weight)
cost_tables(id, org_id, kind, key, value, source, as_of)
launch_events(id, sku_family, event_date, event_type, source_url)
decay_params(id, sku_family, grade, rate_per_day, fitted_at, model_version)
decisions(id, unit_id, created_at, model_version, risk_profile, recommended_channel, confidence,
          fallback_used, candidates_json, reasons_json, flip_conditions_json,
          data_freshness_json, input_snapshot_hash, exploration_propensity)
overrides(id, decision_id, user_id, chosen_channel, reason_text, created_at)
outcomes(id, unit_id, decision_id, channel_taken, sale_price, fees_actual, repair_cost_actual,
         logistics_actual, days_to_disposition, final_status, recorded_at)
audit_log(id, org_id, actor, action, entity, entity_id, payload_json, created_at)
```

Rules: `decisions` and `outcomes` are append-only. Every table carries `org_id` from Phase 5 onward. `is_synthetic` flags keep synthetic data out of real reports.

---

## Appendix C: Repository structure

```
secondroute/
├── PLAN.md
├── README.md
├── LICENSE
├── docker-compose.yml
├── Caddyfile
├── .github/workflows/ci.yml
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── src/secondroute/
│   │   ├── api/          # routers
│   │   ├── identity/     # Phase 1
│   │   ├── intake/       # Phase 1
│   │   ├── condition/    # Phase 2
│   │   ├── pricing/      # Phase 2 (interface), Phase 3 (adapters)
│   │   ├── costs/        # Phase 2
│   │   ├── decision/     # Phase 2
│   │   ├── instructions/ # Phase 2 templates, Phase 5 LLM
│   │   ├── feedback/     # Phase 4
│   │   ├── analytics/    # Phase 4
│   │   ├── ingest/       # Phase 3 adapters and imports
│   │   ├── admin/
│   │   └── core/         # config, db, auth, logging
│   └── tests/
├── pipelines/            # Prefect flows (Phase 3+)
├── ml/
│   ├── synthetic/        # Phase 2
│   ├── notebooks/        # exploration only
│   └── models/           # definitions only, no weights in git
├── frontend/
│   └── src/ (pages, components, api, offline)
├── data/
│   ├── seeds/            # CSVs with source and as-of columns
│   └── fixtures/         # small test data
└── docs/
    ├── decisions/        # ADRs
    ├── runbooks/         # restore, rotate keys, add a source
    └── data-sources.md   # Appendix D, with retrieval log
```

---

## Appendix D: Data sources and licenses

| Source | Used in | Access | License or terms | Notes |
|---|---|---|---|---|
| Synthetic generator (in-house) | Phase 2 onward | Local | Project license | Always tagged `is_synthetic` |
| Manufacturer spec sheets | Phase 1 | Manual entry | Public facts | Curated seed, not scraped |
| Wikidata | Phase 1 (optional) | SPARQL | CC0 | Canonical IDs |
| eBay Browse API | Phase 3 | Free developer key | eBay API terms | Active listings only, attribution required |
| eBay Marketplace Insights (sold) | Phase 3 (optional) | Restricted, apply | eBay API terms | May be denied, do not depend on it |
| Partner CSV imports | Phase 3, 5 | Upload | Partner agreement | Highest-priority price signal |
| FRED API | Phase 3 | Free API key | Public data, FRED terms | Monthly, lagged, verify series IDs |
| Wikimedia Pageviews API | Phase 3 | No key, User-Agent required | CC0 data, Wikimedia policies | Demand proxy |
| Google Trends (pytrends) | Optional | Unofficial library | Google terms, fragile | Cache aggressively or skip |
| iFixit API | Phase 2 or later (optional) | Free API | Content may be CC BY-NC-SA | Commercial use restricted, use facts only |
| Kaggle or UCI datasets | Phase 2 prototyping | Download | Check each license | Not for production without license check |
| NIST SP 800-88 Rev. 1 | Phase 2, 5 | Public document | US government work | Basis for wipe certificates |
| PHMSA, DOT battery rules | Phase 2 | Public regulation | Public | Information only |
| R2, e-Stewards directories | Phase 2 | Public lists | Public | Verify current status |
| IRS Pub 526, 561 | Phase 2 | Public | Public | Information only, not tax advice |

**Excluded:** Keepa, DRAMeXchange, Jungle Scout, scraping sites whose ToS prohibit it, any Apple or retailer data without authorization, and any paid LLM API as a hard dependency.

---

## Appendix E: Risks by phase

| Phase | Risk | Mitigation |
|---|---|---|
| 2 | Synthetic prices create false confidence | Badge on every card, separate reporting, no money claims |
| 3 | Thin free market price data | Partner data priority, wider intervals when sample is small |
| 3 | eBay sold data denied | Partner data path is the plan, not a fallback |
| 3 | Component prices stale | `as_of` on every value, staleness flag in UI |
| 4 | Outcome data too sparse to calibrate | Report ECE with sample size, do not claim calibration below minimum |
| 5 | Wrong call destroys trust | Confidence gating, flip conditions, human approval in pilot |
| 5 | Backtest leaks future data | Look-ahead test fails the build |
| 5 | Cross-tenant data leak | RLS tests in CI |
| 6 | Exploration harms a customer's returns | Caps, exclusions, propensity logging, conservative default |
| 6 | Copyleft or restricted model license | License gate before any model is loaded |
| 7 | Scope creep into marketplace | "Never build" list stays in the plan and in ADRs |
| 8 | A 3D view that shows a plausible but wrong shape | The landscape is drawn from the engine's own Monte Carlo samples; the endpoint that feeds it is tested for determinism |
| 8 | A canvas that silently renders nothing | A WebGL support probe and a two-dimensional fallback; a blank region is a build failure |
| 8 | A design system that drifts | The primitives own the tokens; a page that hard-codes a colour or a radius is a review failure |

---

## Appendix F: Open questions

- Which laptop families are in the partner's return mix? Sets the Phase 1 seed.
- Which channels does the partner use today, and what is their baseline net per unit? Needed for Phase 5 backtest.
- What is the partner's risk profile (cash-constrained, or can absorb variance)? Sets Phase 2 defaults.
- Does the partner have a liquidator relationship that can supply bid data? Affects Phase 3 and 7.
- Where will staging run (cloud free tier, partner's server, or our hardware)? Needed for Phase 5.
- What minimum number of outcomes does the pilot commit to? Gates Phase 6.
