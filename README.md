# SecondRoute

**One return in. One disposition instruction out.**

SecondRoute is an open-source decision engine for returned electronics. It helps retailers, brands, and reverse-logistics operators inspect each returned unit and instantly get the highest-value disposition channel — resell, refurbish, parts harvest, recycle, donate, or hold — backed by math, not guesswork.

---

## The Problem

When a warehouse receives a returned laptop, phone, or appliance, staff must decide what to do with it. Today that decision is made by:

- A single fixed rule for all units
- One liquidator contract for everything
- Supplier return policies that reject 40–45% of units
- Gut feel

Every wrong call loses margin. In India alone, stuck returned electronics represent an estimated **$1–5B/year** in recoverable value.

---

## What SecondRoute Does

**Input:** Inspector enters SKU, serial, battery health, cosmetic grade, functional test results, accessories, and photos.

**Engine runs:** Grade distribution → Monte Carlo simulation (10,000 draws) across all 6 channels → Certainty-equivalent ranking (conservative/balanced/aggressive) → Confidence gate.

**Output — one Action Card:**
- Recommended channel with confidence score
- Net value range (p10 / p50 / p90)
- Top 5 alternatives with value deltas
- Top reasons why this channel won
- Flip conditions (e.g., "If battery health > 85%, channel flips to RESELL")
- Step-by-step operator instructions (NIST 800-88 wipe, 4-angle photo, label)
- **Reproducible proof:** Every decision stores an input snapshot + SHA-256 hash. One API call replays it bit-for-bit.

**If confidence < 70%:** Returns `SAFE_DEFAULT` (highest floor value) and flags for human review.

---

## Who It's For

| Role | Value |
|------|-------|
| **Online electronics sellers (India)** | Recover more per return, avoid blind liquidation at 15–20% MRP |
| **Brands running recommerce** | Consistent, auditable grading across warehouses |
| **3PLs / reverse-logistics operators** | Faster inspector calls (<90 sec vs 3–5 min), explainable decisions |
| **Refurbishers & liquidators** | Per-unit buy-side valuation, not bulk averages |

---

## Key Differentiators

| Feature | SecondRoute | Typical Approach |
|---------|-------------|------------------|
| Per-unit math | Monte Carlo × 6 channels | One rule for all |
| Uncertainty | Full distributions (p10/p50/p90) | Single point estimate |
| Risk awareness | Certainty-equivalent utility | Mean-only ranking |
| Confidence gate | `SAFE_DEFAULT` + human escalation | None |
| Explainability | Reasons + flip conditions | Black box |
| Audit trail | Snapshot hash + replay | Spreadsheet / none |
| Data source flexibility | `PriceSource` protocol (synthetic → real) | Hardcoded or single feed |

---

## Current Status

**Phase 11 complete** — Production-ready core with:

- Full intake → inspection → decision → action card flow
- Batch decisions (500+ units)
- Offline-first inspection (IndexedDB queue, auto-sync)
- Auth + tenant isolation (PostgreSQL RLS)
- Analytics: north star, regret, calibration, override rates
- Historical backtest with look-ahead detection + bootstrap CI
- Shop window (public storefront on separate port)
- Retailer self-signup, 12-category catalogue
- Design system + 3D spatial decision console
- All prices synthetic (clearly badged) — real data adapters ready

**Test coverage:** 910 backend tests, 169 frontend tests, 26 E2E visual routes.

---

## Quick Start (for Evaluation)

```bash
# One command starts everything
make dev

# Application at http://localhost:5173
# Landing page at http://localhost:5173/welcome
# Shop window at http://localhost:5174
```

Requires: `uv`, Node, PostgreSQL 16. See [docs](docs/) for detailed setup.

---

## For Retailers: Pilot Program

We're looking for design partners in India processing **≥1,000 returns/month** to run a measured pilot against your current baseline.

**What you provide:** Return volume, inspector access, outcome data (sale price, fees, days to sell).

**What you get:** Deployed instance, onboarding, backtest report showing incremental recovery, calibrated model.

**Business model (to validate):** Flat platform fee + share of incremental recovered value.

**Contact:** [Add your contact here]

---

## Architecture at a Glance

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Inspector  │────▶│  Decision Engine │────▶│   Action Card   │
│  (Web UI)   │     │  (FastAPI/NumPy) │     │  (React/3D)     │
└─────────────┘     └────────┬─────────┘     └─────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Prices  │  │  Costs   │  │ Components│
        │ (eBay,   │  │ (tables) │  │ (FRED,   │
        │ partner) │  │          │  │  teardown)│
        └──────────┘  └──────────┘  └──────────┘
```

---

## Data Sources (All Free / Partner)

| Source | Purpose | License |
|--------|---------|---------|
| eBay Browse API | Active listing prices | eBay API Terms |
| FRED | Component commodity prices | Public Domain |
| Wikimedia Pageviews | Demand proxy | CC0 |
| Partner CSV imports | Sold transaction data | Partner Agreement |
| Synthetic generator | Prototyping / fallback | MIT (project) |

**Hard constraint:** No paid APIs as hard dependencies. No ToS-violating scraping.

---

## Documentation

- [PLAN.md](PLAN.md) — Full phased build plan (11 phases, 56 features)
- [PROGRESS.md](PROGRESS.md) — Feature-level build tracker
- [CHANGELOG.md](CHANGELOG.md) — Release history
- [docs/decisions/](docs/decisions/) — Architecture Decision Records (ADRs)
- [docs/data-sources.md](docs/data-sources.md) — Data source register
- [docs/runbooks/](docs/runbooks/) — Operational runbooks

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Contributing

Read [AGENTS.md](AGENTS.md) for multi-agent working rules. All work must trace to a feature ID from PLAN.md.