"""
Historical backtest (Phase 5 - F5.6).

Replays past decisions using only the information each decision had at the
time it was made, and compares the engine against the partner's baseline
policy.

The public surface:

- :mod:`secondroute.backtest.lookahead` - the look-ahead detector
- :mod:`secondroute.backtest.bootstrap` - the bootstrap interval
- :mod:`secondroute.backtest.baseline` - the baseline policies
- :mod:`secondroute.backtest.engine` - the runner
"""

from secondroute.backtest.baseline import (
    BaselinePolicy,
    FixedChannelBaseline,
    MostCommonChannelBaseline,
)
from secondroute.backtest.bootstrap import (
    BootstrapError,
    ConfidenceInterval,
    bootstrap_mean_ci,
)
from secondroute.backtest.engine import (
    BacktestResult,
    BacktestRunError,
    SkippedDecision,
    run_backtest,
)
from secondroute.backtest.lookahead import (
    LookAheadError,
    LookAheadFinding,
    LookAheadReport,
    check_decision,
    check_decision_with_relations,
)

__all__ = [
    "BacktestResult",
    "BacktestRunError",
    "BaselinePolicy",
    "BootstrapError",
    "ConfidenceInterval",
    "FixedChannelBaseline",
    "LookAheadError",
    "LookAheadFinding",
    "LookAheadReport",
    "MostCommonChannelBaseline",
    "SkippedDecision",
    "bootstrap_mean_ci",
    "check_decision",
    "check_decision_with_relations",
    "run_backtest",
]
