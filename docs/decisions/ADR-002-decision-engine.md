# ADR-002: Decision Engine Design

## Status
Accepted

## Context
Phase 2 delivers the core of SecondRoute: given an inspected returned unit, the
system must recommend a disposition channel with an explicit confidence, a net
value range, reasons, and the conditions under which the answer would change.

Three constraints shaped the design:

1. **Reproducibility.** A decision must be explainable and replayable months
   later, when the price data and the cost tables have moved on. That rules out
   anything that depends on ambient state at read time.
2. **Honesty about uncertainty.** The product's whole value is that the
   operator knows *how sure* the system is. A recommendation without a
   calibrated confidence is worse than no recommendation.
3. **No LLM in the decision path.** The LLM writes words; it never picks a
   channel or a number (PLAN.md principle 3).

The engine also has to work with synthetic prices in Phase 2 and real prices in
Phase 3, without changing the decision code.

## Decision

We adopt the following design.

### 1. The engine is a pure function of an input snapshot

```
snapshot -> evaluation -> ranking -> confidence gate -> explanations
```

The snapshot captures the unit, the inspection signals, the grade
distribution, the eligibility rules, the whole cost book, the channel list, the
risk profile, the sample count, the seed, the threshold and the `as_of`
timestamp. The snapshot is hashed (SHA-256 over canonical JSON) and stored with
the decision. Replaying a decision means feeding the stored snapshot back in.

**Consequence:** `as_of` is part of the snapshot, so two API calls that do not
pin `as_of` legitimately differ. The API accepts an explicit `as_of` for
backtests and for byte-identical reruns.

### 2. Prices come from a protocol, not a provider

```python
class PriceSource(Protocol):
    async def get_distribution(self, sku_id, grade, channel, as_of) -> PriceDistribution: ...
```

`PriceDistribution` is a **weighted empirical distribution** over observed
prices, not a fitted parametric family. A cell backed by three observations
produces a coarse distribution, which lowers confidence and can trigger
`SAFE_DEFAULT`. That is the honest behaviour: thin data should reduce
confidence, not hide behind a well-fitting curve.

Phase 2 ships two adapters (`SyntheticPriceSource`, `DatabasePriceSource`);
Phase 3 adds real ones. The engine does not change.

### 3. Grade rules are explicit and monotone

The inspection signals build a *condition score*:

```
score = 0.68 * cosmetic + 0.22 * battery - 0.38 * failure_rate
```

The score maps linearly onto an *expected grade level* on the 1-4 scale
(1 = grade D, 4 = grade A). The four grades then get a discretised-Gaussian
spread around that level, with a small uniform floor so no grade is impossible.

Because the expected level is monotone increasing in battery health, and
`P(A)` is monotone increasing in the expected level, **worse battery health can
never increase the probability of grade A**. That invariant is asserted by the
test suite.

> This replaced an earlier softmax design in which the score was added to every
> grade's logit. A uniform shift cancels out of a softmax, so the score had no
> effect at all. The location-shift model is what actually satisfies the
> monotonicity requirement.

### 4. Channel evaluation is a seeded Monte Carlo simulation

For every eligible channel, 10,000 draws are taken from the sale-price, fee,
repair, logistics and holding distributions. Cost components carry their own
dispersion (repair is the noisiest at 30 % CV; the platform fee is exact).

The net value is

```
net = sale_price - fees - logistics - handling - repair - holding
```

Channel eligibility is deterministic policy, not a model: an activation lock
blocks both resale channels, and an expected grade level below 2.4 blocks
open-box.

Sub-seeds are derived per (seed, channel, grade) via SHA-256, so the result
does not depend on iteration order and changing one channel never shifts
another.

### 5. Ranking uses the certainty equivalent

```
certainty_equivalent = mean - lambda * stddev
```

`lambda` comes from configuration: conservative 2.0, balanced 1.0, aggressive
0.5. The conservative profile prefers the lower-variance channel; the
aggressive profile prefers the higher expected value.

### 6. Confidence requires the recommendation to be uniquely best

For each Monte Carlo draw the engine finds the best net and computes a 5 %
margin around it. A channel is "within the margin" when it is no more than
5 % away from the best net in that draw.

**Confidence is the probability that the recommended channel is the only
channel inside that margin.** If a rival channel is just as good in a draw,
that draw does not count as a confident recommendation.

> The plan's literal wording is "P(recommended channel is within 5 % of the
> best net)". Taken alone that would give *high* confidence to two
> indistinguishable channels, which is the opposite of what the acceptance
> criteria require. The uniqueness requirement is what makes overlapping
> distributions fall back to `SAFE_DEFAULT` while a clear winner passes.

When confidence is below the threshold (default 0.70) the engine returns
`SAFE_DEFAULT` and records the conservative floor - the eligible channel with
the highest p10 net - separately.

### 7. Explanations are derived from the numbers, never invented

**Reasons** are the largest contributors to the net difference between the
recommended channel and the runner-up, computed from the cost breakdown. They
cannot contradict the numbers on the card.

**Flip conditions** are found by a one-at-a-time sensitivity search. Numeric
inputs use bisection to find the nearest threshold at which the recommendation
changes; categorical inputs try every alternative value. The search uses a
reduced sample count (2,000) for latency, and the threshold is stored at full
precision so the flip is exactly reproducible.

### 8. Action steps are static templates

One template per channel, plus a `SAFE_DEFAULT` template that starts with a
human inspection step. No LLM is involved in Phase 2.

## Consequences

### Positive
- Every decision is reproducible from a stored snapshot.
- The engine works identically with synthetic and real price data.
- The monotonicity of the grade rules is provable, not hoped for.
- Confidence is conservative by construction: a decision that is not clearly
  better than the alternative falls back to a human check.
- Explanations cannot drift away from the numbers.

### Negative
- The grade rules are hand-tuned constants, not learned. They are documented
  and easy to change, but they will need recalibration against real outcomes
  in Phase 4.
- The flip-condition search runs many evaluations, so it is the slowest part
  of the engine. It uses a reduced sample count, which makes the thresholds
  approximate (by roughly 1e-4 in the searched range).
- The `organizations` and `users` tables had to be created in Phase 2 because
  the Phase 1 and Phase 2 tables carry foreign keys to them. Their behaviour
  (auth, roles, row-level security) still arrives in Phase 5.

### Neutral
- Confidence, risk profiles, sample count and seed are all configuration
  driven, so a retailer can be tuned without a code change.
- `SAFE_DEFAULT` is a value of `recommended_channel` rather than a separate
  channel, with `fallback_used` and `fallback_channel` alongside it.

## Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Fitted parametric price model (log-normal) per cell | Smooth, always has a shape | Hides thin data; a cell with two observations looks as confident as one with two hundred | The empirical distribution makes thin data *look* thin, which feeds the confidence gate |
| Decision tree / gradient boosting on inspection features | Learns non-linear interactions | Not explainable as a cost breakdown; hard to reproduce months later | Phase 4 measures whether the rules are any good; a learned model can replace them once there is outcome data |
| LLM writes the reasons and the action steps | Reads better | Can invent numbers; not reproducible | The validator in F5.7 exists for a reason, but the decision card should not need one |
| Point estimate with a confidence interval | Simpler | Loses the shape of the outcome distribution; no P(best) | The operator needs to compare channels, not just get a number |
| Sorting channels by mean net | Simplest possible | Ignores risk entirely; the conservative profile has nothing to do | F2.6 requires the risk profiles to matter |
| Flip conditions computed by finite differences | Cheap | Unstable near boundaries; no threshold value to report | Bisection finds the threshold directly and reproducibly |

## Implementation Notes

- `backend/src/secondroute/decision/evaluator.py` - the Monte Carlo engine
- `backend/src/secondroute/decision/utility.py` - risk profiles and the
  certainty equivalent
- `backend/src/secondroute/decision/confidence.py` - the confidence metric and
  the `SAFE_DEFAULT` gate
- `backend/src/secondroute/decision/explanations.py` - reasons and flip
  conditions
- `backend/src/secondroute/decision/engine.py` - the orchestrator
- `backend/src/secondroute/condition/grades.py` - the grade rules
- `backend/src/secondroute/pricing/protocols.py` - the `PriceSource` protocol
- `backend/tests/phase2/` - the test suite (168 tests)

## Related ADRs
- ADR-001: Technology Stack Selection
- ADR-003: Database Schema and Migration Strategy (to be created)

## References
- PLAN.md Phase 2, features F2.1 to F2.11
- PLAN.md principle 3: "The LLM writes words, not decisions"
- NIST SP 800-88 Rev. 1 - media sanitisation, referenced by the action steps

---

*Date: 2026-10-20*
*Author: ai-nemotron-ses_eaa6f421*
*Reviewers: —*