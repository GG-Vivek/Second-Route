# ADR-003: Market Intelligence Design

## Status
Accepted

## Context
Phase 3 replaces the synthetic prices of Phase 2 with real, free data, and
adds three new signals: component prices, demand, and the launch calendar.

Five constraints shaped the design:

1. **The decision code must not change.** PLAN.md is explicit: "Decision code
   does not change; only adapters and data do." Phase 2 built the engine around
   a `PriceSource` protocol for exactly this reason, but Phase 3 needed two new
   *channels* (`PARTS_HARVEST` and `HOLD`) and a new *signal* (component
   prices), which the protocol alone does not cover.
2. **Everything must be free.** The plan's hard constraint. FRED, Wikimedia and
   the eBay Browse API all have free tiers; partner CSVs are free by
   definition. No paid API is a hard dependency.
3. **Thin data must look thin.** A price fitted from three observations should
   not look like a price fitted from three thousand.
4. **Provenance is not optional.** Every number on the card must be traceable
   to a source and an as-of date.
5. **No scraping that violates terms.** Official APIs, public datasets, and
   partner data under agreement. Nothing else.

## Decision

### 1. The engine keeps one price source; a composite dispatches per channel

The engine still takes a single `price_source` and asks it for a distribution.
A new `CompositePriceSource` dispatches to a per-channel source and falls back
to a default. A second `FallbackPriceSource` tries each source in turn, so
stored observations are preferred and the synthetic source is the fallback.

The engine's own code is unchanged. The channels it can evaluate grew from
four to six, which is a configuration change, not a logic change.

**Why not** a channel-specific branch inside the engine? Because the moment
the engine knows what a channel is, the engine starts making channel-specific
decisions, and the next change would be a channel-specific rule in the
evaluator. The dispatch belongs in the adapter layer, where it can be tested
without touching the engine.

### 2. Prices are empirical, not fitted

`PriceDistribution` holds the observations themselves plus their weights, not
a fitted parametric family. A cell with three observations produces a coarse
distribution, which lowers the confidence and can trigger `SAFE_DEFAULT`.

This is the opposite of what a "clean" pipeline usually does, and it is
deliberate: the confidence gate is supposed to fire when the evidence is
thin, and it can only do that if thinness is visible in the distribution.

### 3. The quantile model steps aside when the data is thin

LightGBM quantile regression (one model per quantile, native API so
scikit-learn is not needed) predicts p10/p50/p90 per family and grade. Below
the sample threshold - 30 observations by default - the model is **not used**
and the empirical quantiles of the cell are used instead.

The pinball loss of every quantile is logged per model version, so a model can
be compared with the one it replaced.

### 4. Cleaning happens before the distribution is built

MAD-based outlier removal, grade normalisation and recency weighting are
applied in the adapter layer, in that order:

- **MAD, not a standard deviation.** A single mispriced listing inflates the
  standard deviation enough to survive its own filter. The median absolute
  deviation is not moved by the outlier it is looking for.
- **Grade normalisation** maps every source's labels onto our canonical
  A/B/C/D. eBay says "Very Good", a partner CSV says "B+", a refurb shop
  says "Refurbished". An unrecognised label returns `None` rather than being
  forced into a bucket.
- **Recency weighting** is an exponential decay with a 30 day half-life, so a
  60 day old observation counts a quarter as much as a fresh one.

### 5. A FRED index is a signal, not a price

The FRED series the plan points at are producer price *indices*. An index
tells you the direction and the rough magnitude of a component's price, not
the price. So the value is scaled by a configured factor and stored with a
reduced confidence weight (0.25-0.35 against 1.0 for a direct quote).

A decision that leans on a FRED-derived component price should be trusted
less than one that leans on a partner quote, and the card says which it was.

### 6. Parts are worth what survives the teardown, less the labour

```
parts value = sum(component price * yield ratio * confidence) - labour
```

A failed functional test condemns the component it belongs to, so a unit with
a broken display is worth less than the same unit with a working one. The
component's source and as-of date are carried through to the card.

`PARTS_HARVEST` is always *eligible* - there is always something to harvest
- but the valuation decides whether it is worth doing. When nothing is
recoverable the channel is worth zero, not an error.

### 7. HOLD needs both a rising price and no launch

Holding is only offered when the expected change over the window is positive
**and** the probability of a launch inside the window is below the threshold.
A known launch the day after today blocks holding outright.

The price rate is fitted as the log-slope of the price against time, per family
and grade, from the price observations. A positive slope means the price is
rising. The HOLD channel's price is the *expected future price*, not today's.

### 8. A stale source lowers the confidence and says so

`GET /api/v1/sources/health` reports every source: when it last spoke,
whether what it said is fresh, and how many times it has failed.

When a source behind a decision is stale, the confidence is multiplied by the
configured degradation factor and the card carries a warning naming the
stale source. A decision made on last month's prices should not look as sure
as one made this morning.

### 9. A channel with no price data is skipped, not fatal

If a price source has no data for a channel, that channel is marked
ineligible with the reason recorded, and the decision continues. A missing
price source is a reason not to recommend that channel - not a reason to
recommend nothing.

## Consequences

### Positive
- The decision engine is unchanged between Phase 2 and Phase 3. The diff is
  in the adapters.
- Every number on the card is traceable: source, as-of date, confidence
  weight.
- Thin data reduces confidence instead of hiding behind a fitted curve.
- The engine prefers real data and falls back to synthetic, so the prototype
  keeps working before any real data exists.

### Negative
- The FRED scale factors are rough. A component priced from a scaled index is
  an estimate, and the confidence weight says so.
- The demand signal is stored but unused. It is a feature waiting for a model
  that can prove it belongs in a price.
- The quantile model needs at least 30 observations in a cell before it is
  used at all, so early on most cells use the empirical distribution.
- The flip-condition search runs many evaluations, so it uses a reduced
  sample count and its thresholds are approximate.

### Neutral
- The launch calendar is manually curated. That is deliberate: the source URL
  of every event is recorded, and a wrong event is auditable.
- The component price and demand tables are in the `ingest` package with the
  other inbound data, even though the decision engine reads them.

## Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Channel-specific logic in the engine | Direct | The engine starts knowing about channels; every later change is channel-specific | Dispatch belongs in the adapter layer |
| Fitted parametric price per cell | Smooth, always has a shape | Hides thin data behind a curve that fits | The empirical distribution makes thinness visible to the confidence gate |
| Outlier removal by standard deviation | Simple | The outlier inflates the very statistic used to find it | MAD is not moved by the outlier |
| Treating a FRED index as a price | Direct number | Overstates the precision by an order of magnitude | Scale it and cut the confidence weight instead |
| Always offering HOLD for a rising price | Simple | A launch tomorrow makes holding a loss | Both conditions, and the launch calendar is the point of the feature |
| A scheduled job for the FRED pull | Runs itself | Needs a scheduler, a worker and a queue | The endpoint the job would call is enough; the scheduler is Phase 5 infrastructure |
| Scraping eBay's public pages | No API key needed | Violates the terms of service | The free Browse API exists for this |

## Implementation Notes

- `backend/src/secondroute/ingest/` - the inbound data: sales import,
  component prices, FRED, demand, launch calendar
- `backend/src/secondroute/pricing/cleaning.py` - F3.3
- `backend/src/secondroute/pricing/quantile.py` - F3.4
- `backend/src/secondroute/pricing/composite.py` - the dispatch
- `backend/src/secondroute/decision/parts.py` - F3.6
- `backend/src/secondroute/decision/hold.py` - F3.8
- `backend/src/secondroute/admin/health.py` - F3.9
- `backend/tests/phase3/` - the test suite
- Alembic revision `0002_phase3_market_intelligence`

## Related ADRs
- ADR-001: Technology Stack Selection
- ADR-002: Decision Engine Design

## References
- PLAN.md Phase 3, features F3.1 to F3.9
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
- Wikimedia REST API: https://api.wikimedia.org/wiki/Core_REST_API
- eBay Browse API: https://developer.ebay.com/api-docs/buy/browse/overview.html

---

*Date: 2026-10-20*
*Author: ai-nemotron-ses_eaa6f421*
*Reviewers: —*