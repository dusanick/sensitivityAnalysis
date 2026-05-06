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


def summary_statistics(
    df: pd.DataFrame,
    metrics: list[str],
    baseline_row: pd.Series | None = None,
) -> pd.DataFrame:
    """Build Summary Statistics table for the given metrics.

    Returns a DataFrame with metrics as columns and statistics as rows:
      Count, Min, Max, Median, Average, Baseline Value,
      % Delta to Average, % Delta to Median, Baseline Percentile.

    Baseline-dependent rows are filled with NaN when *baseline_row* is None.
    """
    stats: dict[str, list] = {}
    row_labels = [
        "Count",
        "Min",
        "Max",
        "Median",
        "Average",
        "Baseline Value",
        "% Delta to Average",
        "% Delta to Median",
        "Baseline Percentile",
    ]

    for m in metrics:
        col = df[m].dropna() if m in df.columns else pd.Series(dtype=float)
        count = col.count()
        col_min = col.min() if count > 0 else np.nan
        col_max = col.max() if count > 0 else np.nan
        col_median = col.median() if count > 0 else np.nan
        col_avg = col.mean() if count > 0 else np.nan

        if baseline_row is not None and m in baseline_row.index and pd.notna(baseline_row[m]):
            bv = float(baseline_row[m])
            delta_avg = (bv - col_avg) / col_avg if col_avg != 0 else np.nan
            delta_med = (bv - col_median) / col_median if col_median != 0 else np.nan
            percentile = (col <= bv).sum() / count if count > 0 else np.nan
        else:
            bv = np.nan
            delta_avg = np.nan
            delta_med = np.nan
            percentile = np.nan

        stats[m] = [count, col_min, col_max, col_median, col_avg,
                    bv, delta_avg, delta_med, percentile]

    return pd.DataFrame(stats, index=row_labels)
