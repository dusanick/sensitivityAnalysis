import numpy as np
import pandas as pd
import pytest

from app.analytics import (
    delta_vs_baseline,
    metric_by_param_level,
    summary_statistics,
)


@pytest.fixture
def grid_df():
    rows = []
    for a in [10, 20, 30]:
        for b in [1, 2]:
            rows.append({"p_a": a, "p_b": b, "ROR": a + b, "MaxDD": -(a + b)})
    return pd.DataFrame(rows)


def test_metric_by_param_level_groups_correctly(grid_df):
    out = metric_by_param_level(grid_df, "p_a", "ROR")
    assert list(out["level"]) == [10, 20, 30]
    # mean of (a+1, a+2) per level == a + 1.5
    assert list(out["mean"]) == [11.5, 21.5, 31.5]
    assert all(out["count"] == 2)


def test_delta_vs_baseline_computes_pct():
    s = pd.Series([10.0, 20.0, 0.0])
    out = delta_vs_baseline(s, 10.0)
    assert list(out["abs_delta"]) == [0.0, 10.0, -10.0]
    assert list(out["pct_delta"]) == [0.0, 100.0, -100.0]


def test_delta_vs_baseline_handles_zero_baseline():
    s = pd.Series([1.0, 2.0])
    out = delta_vs_baseline(s, 0.0)
    assert out["pct_delta"].isna().all()


# ---------------------------------------------------------------------------
# summary_statistics tests
# ---------------------------------------------------------------------------
@pytest.fixture
def runs_df():
    return pd.DataFrame({
        "ROR": [10.0, 20.0, 30.0, 40.0, 50.0],
        "MaxDD": [-5.0, -10.0, -15.0, -20.0, -25.0],
    })


def test_summary_statistics_no_baseline(runs_df):
    result = summary_statistics(runs_df, ["ROR", "MaxDD"], baseline_row=None)
    assert list(result.index) == [
        "Count", "Min", "Max", "Median", "Average",
        "Baseline Value", "% Delta to Average", "% Delta to Median",
        "Baseline Percentile",
    ]
    assert result.loc["Count", "ROR"] == 5
    assert result.loc["Min", "ROR"] == 10.0
    assert result.loc["Max", "ROR"] == 50.0
    assert result.loc["Median", "ROR"] == 30.0
    assert result.loc["Average", "ROR"] == 30.0
    assert np.isnan(result.loc["Baseline Value", "ROR"])
    assert np.isnan(result.loc["Baseline Percentile", "ROR"])


def test_summary_statistics_with_baseline(runs_df):
    baseline = pd.Series({"ROR": 40.0, "MaxDD": -10.0})
    result = summary_statistics(runs_df, ["ROR", "MaxDD"], baseline_row=baseline)
    assert result.loc["Baseline Value", "ROR"] == 40.0
    # % Delta to Average: (40 - 30) / 30
    assert abs(result.loc["% Delta to Average", "ROR"] - 1 / 3) < 1e-9
    # % Delta to Median: (40 - 30) / 30
    assert abs(result.loc["% Delta to Median", "ROR"] - 1 / 3) < 1e-9
    # Baseline Percentile: 4 values <= 40 out of 5
    assert result.loc["Baseline Percentile", "ROR"] == 0.8


def test_summary_statistics_percentile_lowest(runs_df):
    baseline = pd.Series({"ROR": 10.0, "MaxDD": -25.0})
    result = summary_statistics(runs_df, ["ROR"], baseline_row=baseline)
    # 1 value <= 10 out of 5
    assert result.loc["Baseline Percentile", "ROR"] == 0.2
