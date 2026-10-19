# SecondRoute

> One return in. One disposition instruction out.

SecondRoute is an open-source decision engine for returned electronics. It helps retailers and reverse-logistics operators inspect, value, and route each returned unit to its highest-value disposition channel (resell, refurbish, parts harvest, recycle, donate, hold).

## Status

**Phase 0: Foundation** — In Progress

See [PLAN.md](PLAN.md) for the full phased build plan.
See [PROGRESS.md](PROGRESS.md) for current feature tracking.
See [AGENTS.md](AGENTS.md) for multi-agent working rules.

## Quick Start

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
pip install -e .
uvicorn secondroute.api.main:app --reload

# Run database migrations
alembic upgrade head

# Frontend (in separate terminal)
cd frontend
npm install
npm run dev
```

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
- **ML**: scikit-learn, LightGBM, MLflow
- **Auth**: Keycloak (OIDC)
- **Observability**: Prometheus + Grafana + Loki + OpenTelemetry
- **Infrastructure**: Docker Compose, Caddy for TLS

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