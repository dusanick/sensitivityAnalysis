"""Aggregation helpers for the sensitivity dashboard."""
from __future__ import annotations

import numpy as np
import pandas as pd


def metric_by_param_level(
    df: pd.DataFrame, param: str, metric: str
) -> pd.DataFrame:
    """Return summary statistics of ``metric`` grouped by each level of
    ``param``. Columns: level, mean, median, std, min, max, count."""
    if param not in df.columns or metric not in df.columns:
        return pd.DataFrame(
            columns=["level", "mean", "median", "std", "min", "max", "count"]
        )
    grp = df.groupby(param)[metric]
    out = grp.agg(["mean", "median", "std", "min", "max", "count"]).reset_index()
    out = out.rename(columns={param: "level"}).sort_values("level")
    return out.reset_index(drop=True)


def delta_vs_baseline(
    series: pd.Series, baseline_value: float
) -> pd.DataFrame:
    """Compute absolute and percentage delta of each value vs baseline."""
    abs_delta = series - baseline_value
    pct_delta = np.where(
        baseline_value != 0,
        abs_delta / baseline_value * 100.0,
        np.nan,
    )
    return pd.DataFrame(
        {"value": series.values, "abs_delta": abs_delta.values, "pct_delta": pct_delta},
        index=series.index,
    )
