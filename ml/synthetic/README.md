# Synthetic Data Generator

> Generates the synthetic returns and price observations used to develop, test
> and demo the SecondRoute decision engine before any real market data exists.

**Feature:** `F2.1` (Phase 2 — Decision Engine v0)
**Module:** `ml/synthetic/generator.py`

---

## Guarantees

| Property | Guarantee |
|---|---|
| Determinism | Same seed ⇒ byte-identical dataset. Verified by `dataset_hash()` (SHA-256 over canonical JSON). |
| Isolation | Sub-seeds are derived per concern (`units`, `prices`) via `SHA-256(seed:label)`, so changing one stream never shifts the other. |
| Synthetic tagging | Every record carries `is_synthetic = True`. Synthetic and real observations are never merged silently. |
| No network | Generation is fully local. No external API, no scraping, no paid service. |

---

## Usage

```python
from synthetic.generator import SyntheticReturnGenerator

gen = SyntheticReturnGenerator(seed=42)

rows = gen.generate(500)
print(SyntheticReturnGenerator.dataset_hash(rows))
# -> deterministic hex digest, stable across runs and platforms

prices = gen.generate_price_observations(observations_per_cell=40)
```

From the repository root:

```bash
cd ml && python -c "
from synthetic.generator import SyntheticReturnGenerator
g = SyntheticReturnGenerator(seed=42)
rows = g.generate(1000)
print('rows:', len(rows))
print('hash:', SyntheticReturnGenerator.dataset_hash(rows))
"
```

---

## Distributions

### 1. SKU catalogue

Seven synthetic SKU profiles across four families. The `value_multiplier`
scales the base resale value for the profile.

| Family | Model | Year | Storage | RAM | Value multiplier |
|---|---|---|---|---|---|
| MacBook Pro | M3 Pro | 2023 | 512 GB | 18 GB | 1.00 |
| MacBook Pro | M3 Pro | 2023 | 1 TB | 18 GB | 1.18 |
| MacBook Pro | M3 Max | 2023 | 1 TB | 36 GB | 1.62 |
| MacBook Air | M2 | 2022 | 256 GB | 8 GB | 0.58 |
| MacBook Air | M2 | 2022 | 512 GB | 8 GB | 0.66 |
| ThinkPad X1 Carbon | Gen 11 | 2023 | 512 GB | 16 GB | 0.72 |
| Dell XPS 13 | Plus 9310 | 2022 | 512 GB | 16 GB | 0.61 |

### 2. Return reason

| Reason | Weight |
|---|---|
| `BUYER_REMORSE` | 0.34 |
| `DEFECTIVE` | 0.22 |
| `NOT_AS_DESCRIBED` | 0.16 |
| `NOLONGER_NEEDED` | 0.12 |
| `DAMAGED_IN_TRANSIT` | 0.09 |
| `IDENTIFICATION_ERROR` | 0.04 |
| `OTHER` | 0.03 |

### 3. Order channel

| Channel | Weight |
|---|---|
| `ONLINE` | 0.55 |
| `RETAIL` | 0.31 |
| `MARKETPLACE` | 0.14 |

### 4. Cosmetic grade

| Grade | Weight |
|---|---|
| A | 0.18 |
| B | 0.37 |
| C | 0.31 |
| D | 0.14 |

The generator draws the cosmetic grade independently. The **decision engine**
re-derives the grade distribution from the inspection fields (F2.3); the
generator's grade is a plausible "true" grade used only for synthetic price
realism.

### 5. Battery health

```
battery = clip( Normal(94.0, 4.5) − reason_penalty , 55 , 100 )

reason_penalty = 6.0  for DEFECTIVE
               = 3.5  for DAMAGED_IN_TRANSIT
               = 0.0  otherwise
```

Battery health is the primary driver of the decision engine's grade
distribution, so it is the most carefully modelled field.

### 6. Battery cycles

```
cycles = clip( Gamma(shape=4.0, scale=45.0) + (100 − battery_health) × 2.4 , 5 , 1200 )
```

Cycle count is negatively correlated with battery health: worn batteries tend
to have more cycles.

### 7. Functional tests

Five tests are exercised: `display`, `keyboard`, `ports`, `audio`, `camera`.

```
fail_p = clip( base_p(reason) + (95 − battery_health) × 0.006 , 0 , 0.85 )

base_p: BUYYER_REMORSE 0.02 | DEFECTIVE 0.34 | NOT_AS_DESCRIBED 0.17
        NOLONGER_NEEDED 0.03 | DAMAGED_IN_TRANSIT 0.27
        IDENTIFICATION_ERROR 0.09 | OTHER 0.08
```

### 8. Accessories

| Accessory | Present probability |
|---|---|
| `charger` | 0.94 |
| `box` | 0.78 |
| `cable` | 0.81 |
| `adapter` | 0.72 |
| `documentation` | 0.63 |

### 9. Activation lock

`none` for every unit except `IDENTIFICATION_ERROR` returns, where 45 % carry
`present`. (Only the flag is ever stored — never an Apple ID. See AGENTS.md §10.)

### 10. Received-at timestamps

Uniform over a 365-day window starting `2025-01-01` (configurable via
`start_date` / `horizon_days`).

### 11. Synthetic price observations

For each `(family, grade, channel)` cell:

```
mean = GRADE_BASE_VALUE_USD[grade] × value_multiplier × CHANNEL_VALUE_SHARE[channel]

price ~ LogNormal( mean = log(mean) − cv²/2 , sigma = cv )
```

| Grade | Base value (USD) |
|---|---|
| A | 1450 |
| B | 1150 |
| C | 780 |
| D | 420 |

| Channel | Value share | Price CV |
|---|---|---|
| `RESELL_OPEN_BOX` | 0.92 | 0.12 |
| `RESELL_REFURB` | 0.78 | 0.18 |
| `RECYCLE` | 0.06 | 0.22 |
| `DONATE` | 0.00 | 0.00 |

Log-normal is used because resale prices are right-skewed and strictly
positive. Each observation also carries a uniform weight in `[0.5, 1.0]`.

---

## Relationship to the decision engine

The generator produces **inspection-shaped** rows. They can be loaded into the
`inspections` table so the decision engine can be exercised end to end without
any real warehouse data.

The synthetic price observations map directly onto `price_observations` rows
with `source = "synthetic"` and `is_synthetic = true`. The `SyntheticPriceSource`
adapter (F2.2) serves those rows through the same `PriceSource` protocol the
real adapters will implement in Phase 3 — so swapping in real data changes
nothing in the decision code.

---

## Tests

`backend/tests/test_synthetic.py` covers:

- same seed ⇒ same hash (determinism)
- different seed ⇒ different hash
- every row is tagged `is_synthetic`
- battery health stays inside the documented bounds
- accessory and functional-test rates fall inside the documented envelopes

---

*Last updated: 2026-10-20*
*Version: 1.0*
