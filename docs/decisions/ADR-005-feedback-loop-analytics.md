# ADR-005: The feedback loop analytics

## Status
Accepted

## Context
Phase 4 asks the system to measure its own accuracy: how much value a
disposition choice actually recovered, how often the engine's confidence was
right, and how far the recommended channel was from the best one. Three
constraints shape the design, and they pull against each other.

**Append-only data.** The decisions, the overrides and the outcomes are
append-only records of what happened. A measurement derived from them is
also a fact about the past, so it cannot be revised without rewriting
history.

**Measured and estimated are not the same thing.** When a unit went to one
channel, nobody knows what the other channels would have returned. Any
figure for "what we gave up" is then a model estimate, not a measurement.
Adding the two kinds together and presenting the sum as one number is how a
feedback loop starts lying to its own operators.

**Synthetic and real data must not be mixed.** The engine runs on synthetic
prices until the price adapters are live. A dashboard that merges synthetic
and real numbers shows a number that describes neither.

**The version of the calibration has to be known.** A recalibration changes
what "confidence 0.8" means. If the recalibration is applied silently, a
decision made last month cannot be read against the calibration it was
actually made under, and the reliability curve measures a moving target.

## Decision
We will keep the feedback loop in a dedicated `analytics` package, and we
will make the distinction between a measured and an estimated figure
explicit in the data model rather than in the presentation layer.

**Every regret figure carries a kind.** `regret_measurements.regret_kind` is
either `observed` or `estimated`. An observed regret compares the channels
that were actually tried. An estimated regret takes the best alternative
from the decision's own predictions. The rows are append-only, so a
measurement is never revised.

**The summary never adds the two kinds silently.** `RegretSummary` reports
the observed and the estimated totals apart, and the combined total always
carries a label saying what it is made of (`observed`, `estimated`,
`observed + estimated` or `none`).

**A recalibration is a version.** `calibration_versions` holds every fitted
version, with its isotonic mapping, the sample it was fitted on and the
expected calibration error before and after. Only one version is in force at
a time; the previous ones are kept but deactivated. `decisions.calibration_version`
records the version in force when the decision was made, so a decision can
always be read against the calibration it was made under.

**Every report is split by the kind of data.** The north star, the regret
over time and the override rate are each returned once for the synthetic
data and once for the real data. The API never returns a merged figure, so
a caller has to choose which one to show.

**The export carries its own integrity.** Every exported row carries a hash
of its own contents. Re-importing an export recomputes those hashes and
reports whether the export came back unchanged, rather than writing the
rows back: the underlying tables are append-only, so a re-import would
duplicate them.

The pure functions live apart from the service layer, so the estimators can
be checked against a reference implementation on a fixture: the
Kaplan-Meier curve, the expected calibration error and the isotonic fit are
all plain functions over plain data.

## Consequences
### Positive
- A measured figure and an estimated one can never be confused, because the
  distinction is in the row, not in a label on a chart.
- A recalibration can be rolled back to and reproduced, because every
  version is kept and every decision says which one it used.
- The reliability curve measures a fixed target rather than a moving one.
- The estimators are testable without a database and without a model.
- The export can be checked for tampering without a database.

### Negative
- More tables and more migrations for a phase that is mostly reporting.
- A caller of the analytics API has to handle two sections rather than one,
  which is more work in the frontend.
- The regret of a unit with a single channel is never a fact, so the
  observed series is smaller than the number of returns.

### Neutral
- The append-only rule is kept for the measurements as well as for the
  events. A re-measurement is a new row, not an update.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Compute every figure on the fly, store nothing | No tables, no migrations | The distinction between measured and estimated lives only in the response, and a figure can change when the underlying data is re-read | The feedback loop is the data moat; the measurements have to be durable |
| One column for the regret, with the kind in a separate table | Fewer columns | The kind is then optional per row, and a row without one is ambiguous | One row, one kind: the flag cannot be forgotten |
| Apply the recalibration in place and store only the current mapping | One mapping, no history | The reliability curve then measures a moving target, and old decisions cannot be reproduced | A versioned step, as the plan requires |
| Merge the synthetic and the real data and mark the result | One number to show | The number describes neither data set | The two are always returned apart |
| Re-import an export into the database | A true round trip | The tables are append-only, so a re-import duplicates rows | The import verifies the export instead of writing it back |

## Implementation Notes
- `backend/src/secondroute/analytics/` holds the package: the estimators
  (`time_to_sell.py`, `calibration.py`), the services
  (`predicted_vs_realized.py`, `regret.py`, `reports.py`), the models
  (`models.py`) and the API (`api.py`, `export_api.py`).
- Migrations: `0003_feedback_tables` (the overrides and the outcomes),
  `0006_regret_measurements`, `0007_calibration`.
- The baseline of the north star is the salvage default, `RECYCLE`. When
  that channel was tried for the unit the baseline is its realized net;
  when it was not, the baseline is the model's prediction for it, and the
  two counts are reported apart.

## Related ADRs
- ADR-002: Decision Engine Design
- ADR-003: Market Intelligence Design

## References
- PLAN.md, Phase 4 (F4.1 to F4.8) and Appendix B
- AGENTS.md, the append-only and synthetic-flag rules

---

*Date: 2026-10-20*
*Author: ai-nemotron-ses_eaa59d66*
*Reviewers: ai-minimax-m3.1-flash-ses_ea89089b*
