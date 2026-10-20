# SecondRoute

> One return in. One disposition instruction out.

SecondRoute is an open-source decision engine for returned electronics. It helps retailers and reverse-logistics operators inspect, value, and route each returned unit to its highest-value disposition channel (resell, refurbish, parts harvest, recycle, donate, hold).

## Status

**Phase 2: Decision Engine v0** — Complete (synthetic prices)

| Phase | Status |
|---|---|
| Phase 0 — Foundation | ✅ Complete |
| Phase 1 — Unit Intake and Inspection | ✅ F1.1–F1.7 complete |
| Phase 2 — Decision Engine v0 | ✅ Complete |
| Phase 3 — Market and Component Intelligence | ✅ Complete |
| Phase 4 — Feedback Loop and Analytics | 🔲 Not started |

See [PLAN.md](PLAN.md) for the full phased build plan.
See [PROGRESS.md](PROGRESS.md) for current feature tracking.
See [AGENTS.md](AGENTS.md) for multi-agent working rules.

## What It Does (Phase 2)

Inspect a returned unit, and the engine tells you where to send it, how sure it
is, why, and what would change the answer.

```
inspection -> grade distribution -> Monte Carlo over every channel
            -> certainty-equivalent ranking -> confidence gate
            -> reasons + flip conditions -> action card
```

* **One card out.** Channel, confidence, net range (p10/p50/p90), the
  alternatives with their deltas, the reasons, the flip conditions and the
  operator's action steps.
* **Honest uncertainty.** Below the confidence threshold the engine returns
  `SAFE_DEFAULT` and asks a human to check the unit.
* **Reproducible.** Every decision stores an input snapshot and its SHA-256
  hash. `GET /api/v1/decisions/{id}/reproduce` replays it and proves the match.
* **Prototype, clearly labelled.** Prices and costs are synthetic. The card
  says so, every time.
* **Real data when there is any.** Stored observations are preferred over the
  synthetic source, so the same code path serves both.

### Try it

```bash
cd backend
python scripts/smoke_phase2.py     # end-to-end smoke test, no server needed
```

The script creates a SKU, a unit and an inspection, runs the decision, and
checks the whole card payload. It needs no network and no database server.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/units/{id}/decide` | Run the engine and store the decision |
| `GET` | `/api/v1/decisions/{id}` | Read a stored decision |
| `GET` | `/api/v1/decisions/{id}/reproduce` | Replay a decision from its snapshot |
| `GET` | `/api/v1/units/{id}/decisions` | List a unit's decisions |
| `GET` | `/api/v1/costs` | Read the cost tables |
| `POST` | `/api/v1/costs` | Create a cost value (a `source` is required) |
| `PATCH` | `/api/v1/costs/{id}` | Update a cost value |
| `GET` | `/api/v1/costs/kinds` | Document every cost kind |
| `GET` | `/health` | Liveness and dependency check |
| `POST` | `/api/v1/imports/sales/preview` | See a sales file's columns and suggested mapping |
| `POST` | `/api/v1/imports/sales` | Import a partner sales file (or dry-run it) |
| `GET` | `/api/v1/components/prices` | The component prices, with a staleness flag |
| `POST` | `/api/v1/components/prices/pull-fred` | Pull the configured FRED series |
| `GET` | `/api/v1/sources/health` | When each source last spoke, and whether it is fresh |

## Quick Start

### With Docker

```bash
# Clone and enter
git clone <repo-url>
cd secondroute

# Start infrastructure (PostgreSQL, Redis, Caddy)
docker compose up -d

# Backend (in separate terminal)
cd backend
cp .env.example .env
# Edit .env if needed
pip install -e ".[dev]"
alembic upgrade head
uvicorn secondroute.api.main:app --reload

# Frontend (in separate terminal)
cd frontend
npm install
npm run dev
```

The stack is then on <http://localhost:5173>.

### Without Docker

The backend needs PostgreSQL; Redis is optional (the health check reports
"degraded" without it, and only the session store and the job queue use
it). With PostgreSQL 16 and Node installed, from the repository root:

```bash
# 1. PostgreSQL, with the roles the application and the backup use
brew services start postgresql@16
createdb secondroute
POSTGRES_USER=$(whoami) POSTGRES_DB=secondroute POSTGRES_PASSWORD=secondroute \
  bash docker/postgres/01-create-app-role.sh

# 2. The backend
cd backend
cp .env.example .env
# Set DATABASE_URL to the application role, not the superuser:
#   postgresql+asyncpg://secondroute_app:secondroute@127.0.0.1:5432/secondroute
uv sync
uv run alembic upgrade head
uv run python scripts/load_skus.py        # the SKU catalogue
uv run python scripts/seed_dev_org.py     # an organisation to act for
uv run uvicorn secondroute.api.main:app --reload --port 8000

# 3. The frontend (in another terminal)
cd frontend
npm install
cp .env.example .env                     # VITE_PROXY_TARGET=http://127.0.0.1:8000
npm run dev
```

The frontend is then on <http://localhost:5173>.

> **All the paths above are relative to the repository root.** The role
> script in particular only exists at `docker/postgres/01-create-app-role.sh`
> from the root, so running it from `backend/` fails with
> `No such file or directory`. If you see that, `cd` to the root first.

### Which organisation a request acts for

Every request acts for one organisation, and the row-level security
policies refuse a write that names none. The authentication dependency
takes the organisation from the verified token.

Outside production the organisation can also be named with a header, so
the application can be tried out without a login:

```bash
curl -H "X-Org-Id: <the id seed_dev_org.py printed>" \
     http://127.0.0.1:8000/api/v1/units
```

In production the header is ignored: the only way in is a token.

### Database Migrations

```bash
# Create a new migration
cd backend
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to base
alembic downgrade base

# Show current revision
alembic current

# Show migration history
alembic history
```

## Architecture

- **Backend**: FastAPI + SQLAlchemy 2.x + PostgreSQL 16
- **Frontend**: React 18 + Vite + TypeScript + Tailwind + shadcn/ui
- **Decision engine**: NumPy Monte Carlo, seeded and reproducible
- **ML**: scikit-learn, LightGBM, MLflow
- **Auth**: Keycloak (OIDC)
- **Observability**: Prometheus + Grafana + Loki + OpenTelemetry
- **Infrastructure**: Docker Compose, Caddy for TLS

### Package layout

| Package | Phase | Purpose |
|---|---|---|
| `core/` | 0 | Config, database, structured logging |
| `identity/` | 1 | SKU catalog, serial prefixes, organisations, users |
| `intake/` | 1 | Units, inspections, photos |
| `feedback/` | 1 | Audit log |
| `condition/` | 2 | Grade rules and condition estimates |
| `pricing/` | 2 | `PriceSource` protocol and price observations |
| `costs/` | 2 | Cost tables and their admin API |
| `decision/` | 2 | The decision engine |
| `instructions/` | 2 | Action card templates |
| `ml/synthetic/` | 2 | The synthetic data generator |
| `ingest/` | 3 | Inbound data: sales import, FRED, demand, launch calendar |
| `admin/` | 3 | Source health and operator endpoints |

## Documentation

- [PLAN.md](PLAN.md) — Phased build plan (8 phases, 56 features)
- [AGENTS.md](AGENTS.md) — Multi-agent working rules
- [PROGRESS.md](PROGRESS.md) — Build tracker
- [docs/decisions/](docs/decisions/) — Architecture Decision Records (ADRs)
- [docs/data-sources.md](docs/data-sources.md) — Data source register (licenses, access, rate limits)
- [docs/runbooks/](docs/runbooks/) — Operational runbooks

## License

MIT License — see [LICENSE](LICENSE).

## Contributing

Read [AGENTS.md](AGENTS.md) before contributing. All work must trace to a feature ID from PLAN.md.

## Data Sources

All data sources are free/open or have free tiers. See [docs/data-sources.md](docs/data-sources.md) and PLAN.md Appendix D for the full register with licenses and access methods.

**Hard constraint**: No paid APIs as hard dependencies. No scraping violating ToS.