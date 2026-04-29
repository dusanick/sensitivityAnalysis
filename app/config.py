"""Static defaults shared across the app."""
from __future__ import annotations

# Default metric whitelist mirroring the CONFIG sheet of
# Robustness_Testing_Templates_V1.xlsx. Used only to preselect checkboxes —
# users can override at runtime.
DEFAULT_METRICS: tuple[str, ...] = (
    "ROR",
    "MaxDD",
    "Volatility",
    "UI",
    "Trades",
    "PctWins",
    "AvgWin",
    "AvgLoss",
    "WinLen",
    "Expectancy",
    "ProfitFactor",
    "Sharpe",
    "Sortino",
    "AvgExp",
    "MAR",
    "NetProfit",
)

# Columns that are clearly metadata / identifiers — never treated as metrics
# or parameters by the auto-classifier.
META_COLUMNS: tuple[str, ...] = (
    "Test",
    "Name",
    "Dates",
    "Periods",
    "Comp",
)

# Default heuristic for parameter detection.
DEFAULT_PARAM_PREFIX = "newStrat_"

# Highlight colour for the baseline run in charts (Excel "DARK RED" parity).
BASELINE_COLOR = "#8B0000"
SERIES_COLOR = "#1f77b4"
