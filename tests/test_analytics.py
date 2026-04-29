import pandas as pd
import pytest

from app.analytics import (
    delta_vs_baseline,
    metric_by_param_level,
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
