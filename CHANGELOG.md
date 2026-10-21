# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- A shop window: a separate application in `frontend-public/`, served on port 5174,
  that shows the devices that are for sale with their photographs, their condition,
  their test results and their price. It is public: there is no sign-in, and the
  operator's console is not behind it.
- A public listings endpoint, `GET /api/v1/public/listings` and
  `GET /api/v1/public/listings/{id}`. A listing is a device the engine said to
  sell, whose latest decision still says to sell it, and which has not gone. It
  carries no serial, no return reason, no note, no cost, no confidence and no
  organisation.
- A photograph now says whether it may be published. One of the four angles the
  inspection form takes is a photograph of the label on the bottom of the device,
  and the label carries the serial number: the serial was not in the response, but
  it was in the picture.
- ADR-007 records why the shop window is a separate application rather than a
  second shell on the console, and what it costs.
- The storefront has its own lint, its own tests, its own visual regression suite
  and its own jobs in the CI. The staging stack builds it into its own volume and
  Caddy serves it from its own host.
- A design system and a spatial decision console are now planned as Phase 8. ADR-006
  records the decision, the pmndrs token set, the react-three-fiber dependency
  versions and their licences, and the rule that the 3D view is an enhancement over an
  accessible two-dimensional one rather than a replacement for it.
- The pmndrs Material Design 3 token set, in light and dark, with a theme that is
  remembered and a page that never flashes the wrong one.
- An interface kit of nineteen primitives, and an application shell with a sidebar, a
  glass header and a command palette that puts every destination one keystroke away.
- A decision distribution endpoint that returns the engine's own Monte Carlo draws as
  a density histogram, replayed from the stored snapshot.
- The channel landscape: a flat ridgeline that is always available, and a
  react-three-fiber scene over the top of it for the browsers that can draw it.
- The photographs are served and shown. The model of a unit is returned with the unit.
- A visual regression suite over the critical routes in both themes, run against the
  built application with the API answered from fixtures, so it needs no backend.

### Changed
- The build plan now carries Phase 10 and the risks it comes with: a public
  endpoint that leaks a field of the business's own, a shop window that drifts
  from the console, and a photograph of a serial number.
- The seed marks every unit sold as soon as the first one was sold, because it
  read the running total of the outcomes rather than the outcome of the unit.
  Nothing was ever left on the shelf, so the window was empty. The status of a
  unit now follows what was done with it.
- The build plan now carries Phase 8 and the risks it comes with: a view that shows a
  plausible but wrong shape, a canvas that silently renders nothing, and a design
  system that drifts.
- The coloured badges follow the Material Design 3 pattern: the brand tone is the
  background and the tone that belongs on it is the text. Every badge was unreadable
  in the dark theme; a bright yellow with white text on it is a ratio of about one
  and a half to one.
- There is a way to put a photograph in, and the photograph is written out again from
  its pixels, so that nothing about the camera, the moment or the place survives in
  it. There is a seed that makes a workload to look at: forty units, their
  inspections, four photographs each, the decisions the engine made, the overrides
  and the outcomes.
- The cache is optional, and a dependency that is not configured is not a failure.

### Fixed
- A generator dependency that sits underneath another dependency is torn down as
  soon as the outer one returns, and the session dependency clears the
  organisation when it is torn down. The storefront had a session with no
  organisation on it, and every row was refused.
- The window function over the decisions dragged the decisions table into the
  outer query as well, where it had no join condition. Every listing was
  multiplied by the number of decisions. It reads the columns of an inner query
  now.
- The health page read the object the source-health endpoint answers with as
  though it were a list, and fell into the error boundary. The page is at
  `/status` now, because the front end's page and the back end's health
  endpoint were both at `/health` and the proxy sent that path to the back end.
- The tenant-isolation policies on two tables were never evaluated, because a policy
  only binds the owner of a table when `FORCE ROW LEVEL SECURITY` is set. One
  organisation could read and write another's calibration versions and regret
  measurements, and recalibrating deactivated every other organisation's active
  version.
- The database enums had drifted from the models. Four return reasons, two order
  channels and four unit statuses were refused by the database, and the intake form
  offered all of them.
- The offline queue wrote with `crypto.randomUUID`, which only exists in a secure
  context, so on a machine on a plain address the offline path was dead. A rejected
  entry was written as failed and then never read, so it was posted again on every
  reconnect, for ever.
- The two dialogs declared themselves modal and never moved the focus into
  themselves, trapped the tab key or gave the focus back.
- A commit cleared the organisation, because the setting is transaction-local.
- A failed query was shown as a number of zero on the dashboard and the health page.
- The audit row for a create recorded the new row's identifier and timestamps as
  null.
- The notes on the intake form were collected and thrown away, because there was
  nowhere to put them. There is somewhere now.
- The photographs were not served: the development server and the proxy both
  answered a request for an image with the page itself.
- The visual regression suite was photographing the dark theme twice.
- Every surface uses the new design system: the dashboard, the unit list, the unit
  detail, the two forms, the decision card, the analytics and the backtest.
- The fonts ship with the application. The Google Fonts link is gone, because a
  third-party runtime request is not something a pilot can depend on.
- The decision card shows how much the channels overlap, which is what the confidence
  is made of and what used to be a single percentage.

### Fixed
- The replay of a decision did not bind the price source to the model of the unit, did
  not value the parts and did not consult the launch calendar. It looked like a
  faithful replay and was not one.
- The decision page never showed the decision card, because it fetched the decision
  with an identifier that was null until the operator clicked a row in the history.
- The frontend never named a tenant, so every write was refused and every read came
  back empty.
- The dashboard asked for the health check under the versioned API prefix, where it
  does not live, so it showed an error on every load.

## [0.1.0] - 2026-10-20

The first complete build: Phases 0 through 7 of the build plan, covering the
foundation, the intake and inspection record, the decision engine, the market
intelligence, the feedback loop and analytics, the pilot readiness work, the
learning loop and the ecosystem expansion.

### Added
- **Foundation** — repository, Docker Compose stack, FastAPI backend skeleton,
  Vite and React frontend skeleton, the Alembic migration baseline, the CI
  pipeline, and the data-source register.
- **Intake and inspection** — the SKU catalogue and its idempotent seed, the
  serial prefix lookup, the return intake API, the append-only inspection
  record, photo upload with EXIF and GPS stripped, the intake and inspection
  user interface, and the audit log.
- **Decision engine** — the seeded synthetic returns generator, the
  `PriceSource` protocol, the grade rules, the cost tables, the Monte Carlo
  channel evaluator, the risk profiles and the certainty-equivalent utility,
  the confidence gate and `SAFE_DEFAULT`, the reasons and the flip
  conditions, the decision API with its input snapshot hash, the action card
  templates, and the decision card.
- **Market intelligence** — the eBay Browse API adapter, the partner sold-data
  CSV import, MAD-based price cleaning with recency weighting, the LightGBM
  quantile model, the component prices and the FRED adapter, the parts
  harvest valuation, the Wikimedia demand signal, the launch calendar and the
  `HOLD` logic, and the source health and confidence downgrade.
- **Feedback loop** — the override with a mandatory reason, the outcome log,
  the predicted versus realized view, the Kaplan-Meier time-to-sell model, the
  regret calculation, the calibration and the isotonic recalibration, the
  analytics page, and the CSV data export.
- **Pilot readiness** — Keycloak authentication with roles, tenant isolation
  enforced by PostgreSQL row-level security, the risk profile settings, batch
  decisions, offline inspections with an IndexedDB queue, the historical
  backtest with its look-ahead detection, the explanation text, and the
  staging deployment with the backup and restore drill.
- **Learning loop** — the model registry, shadow mode, the promotion gate,
  drift monitoring, controlled exploration, Thompson sampling, off-policy
  evaluation, the photo condition assist, and the monthly expert review.
- **Ecosystem** — the second category by configuration alone, lot and batch
  optimization, the fraud and wardrobing signals, the upstream return-reason
  insights, the partner integrations, and the data ownership tools.

[Unreleased]: https://example.invalid/secondroute/compare/v0.1.0...HEAD
[0.1.0]: https://example.invalid/secondroute/releases/tag/v0.1.0
