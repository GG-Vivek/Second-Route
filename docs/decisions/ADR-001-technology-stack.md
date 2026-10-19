# ADR-001: Technology Stack Selection

## Status
Accepted

## Context
We need to establish the foundational technology stack for SecondRoute. The PLAN.md Appendix A outlines the approved choices. This ADR formally records these decisions with rationale.

Key constraints:
- All tools, libraries, and services must be free/open source or have a usable free tier (hard constraint from PLAN.md)
- Stack must support: FastAPI backend, React frontend, PostgreSQL database, ML pipelines, observability
- Must be deployable via Docker Compose for local development
- Licenses must be compatible with MIT/Apache-2.0 project license

## Decision
We adopt the technology stack as specified in PLAN.md Appendix A:

| Layer | Choice | License | Rationale |
|-------|--------|---------|-----------|
| Backend language | Python 3.12 | PSF | Mature ML ecosystem, FastAPI native, type hints |
| API | FastAPI, Pydantic v2 | MIT | High performance, OpenAPI auto-generation, validation |
| ORM and migrations | SQLAlchemy 2.x, Alembic | MIT | Mature, async support, migration management |
| Database | PostgreSQL 16 | PostgreSQL License | ACID, JSONB, RLS (Phase 5), proven at scale |
| Analytics | DuckDB, Parquet | MIT, Apache-2.0 | In-process OLAP, Parquet for data exchange |
| Pipelines | Prefect (OSS server) | Apache-2.0 | Python-native, scheduling, observability, free tier |
| Jobs | Redis, RQ | BSD, MIT | Simple, reliable, Redis already in stack |
| Scraping (where permitted) | Scrapy | BSD | Robust, async, middleware, respect robots.txt |
| Browser tests | Playwright | Apache-2.0 | Cross-browser, reliable, good TypeScript support |
| ML | scikit-learn, LightGBM, statsmodels, NumPy | BSD, MIT | Production-ready, no runtime dependencies |
| Experiment registry | MLflow | Apache-2.0 | Tracking, registry, model serving, open source |
| Computer vision | OpenCV, Tesseract or PaddleOCR | Apache-2.0 | Mature, no GPU required for inference |
| Explanation LLM runtime | Ollama | MIT | Local inference, open-weights models, no API costs |
| Frontend | React 18, Vite, TypeScript, Tailwind, shadcn/ui, TanStack Query, Recharts | MIT | Modern, type-safe, component library, server state |
| Offline storage | IndexedDB (browser), `idb` library | MIT | Native browser API, Promise-based wrapper |
| Auth | Keycloak | Apache-2.0 | Full OIDC, RBAC, self-hosted, free |
| Reverse proxy, TLS | Caddy | Apache-2.0 | Automatic HTTPS, simple config, Docker-native |
| Containers | Docker, Docker Compose | Apache-2.0 | Industry standard, local dev/prod parity |
| Photo storage | Local volume (dev), SeaweedFS (prod) | Apache-2.0 | S3-compatible, scalable, open source |
| Metrics, dashboards | Prometheus, Grafana | Apache-2.0, AGPL-3.0 | Standard, powerful, Grafana AGPL noted |
| Logs | Loki | AGPL-3.0 | Labels-based, integrates with Prometheus/Grafana |
| Tracing | OpenTelemetry | Apache-2.0 | Vendor-neutral, auto-instrumentation |
| Tests | pytest, hypothesis, schemathesis, Vitest, Playwright | MIT, Apache-2.0 | Property testing, contract testing, E2E |
| Lint, types | ruff, mypy, eslint | MIT | Fast, comprehensive, TypeScript support |
| CI | GitHub Actions | Service terms | Free for public repos, generous for private |
| Secrets in repo | SOPS | MPL-2.0 | Encrypted secrets in git, age/GPG support |
| Backups | pg_dump, restic | PostgreSQL License, BSD-2 | Standard, incremental, encrypted, multi-backend |

## Consequences
### Positive
- Fully open-source stack with no vendor lock-in
- All components have free tiers suitable for development and pilot
- Strong ecosystem and community support
- Docker Compose enables full local development parity
- Clear license compliance path

### Negative
- Multiple AGPL-3.0 components (Grafana, Loki) require careful deployment isolation
- Self-hosted Keycloak adds operational complexity vs managed auth
- Prefect OSS server requires self-hosting (no managed free tier)
- SeaweedFS less common than MinIO/S3, smaller community

### Neutral
- Python 3.12 minimum version (released Oct 2023)
- React 18 with concurrent features
- TypeScript strict mode required

## Alternatives Considered
| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Node.js/Express | Single language | Weaker ML ecosystem, no native async SQLAlchemy equivalent | Python required for ML |
| Django REST Framework | Batteries included | Heavier, less performant, ORM less flexible | FastAPI better for API-first |
| SQLModel | Built on SQLAlchemy/Pydantic | Younger, less mature migration story | SQLAlchemy 2.x + Alembic proven |
| MongoDB | Flexible schema | No ACID transactions, no RLS, weaker analytics | PostgreSQL required for RLS + analytics |
| Supabase | Managed Postgres + Auth | Vendor lock-in, pricing at scale | Self-hosted required for pilot |
| Next.js | Full-stack React | Server components add complexity, Node.js backend | Separation of concerns, Python ML |
| MinIO | S3-compatible, popular | AGPL-3.0 (copyleft) | SeaweedFS Apache-2.0 |
| Grafana Cloud | Managed observability | Cost at scale, vendor lock-in | Self-hosted free tier sufficient |

## Implementation Notes
- Initialize Docker Compose with PostgreSQL 16, Redis, Caddy (F0.2)
- Backend: FastAPI project structure with `src/secondroute/` layout (F0.3)
- Frontend: Vite + React 18 + TypeScript + Tailwind + shadcn/ui (F0.4)
- Alembic initialized with baseline migration (F0.5)
- CI pipeline with ruff, mypy, pytest, Vitest, compose smoke test (F0.6)
- Create `docs/data-sources.md` with Appendix D sources (F0.7)

## Related ADRs
- ADR-002: Database Schema and Migration Strategy (to be created)
- ADR-003: API Versioning and Contract Strategy (to be created)
- ADR-004: Authentication and Authorization Architecture (Phase 5)

## References
- PLAN.md Appendix A: Technology Stack
- PLAN.md Appendix D: Data Sources and Licenses
- https://fastapi.tiangolo.com/
- https://www.keycloak.org/
- https://caddyserver.com/

---

*Date: 2026-10-20*
*Author: ai-nemotron-ses_eaa6f421*
*Reviewers: —*