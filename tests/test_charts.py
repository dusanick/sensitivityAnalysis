"""Smoke + behaviour tests for the Plotly chart builders."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app import charts
from app.config import BASELINE_COLOR, SERIES_COLOR


@pytest.fixture
def grid_df():
    rows = []
    for a in [10, 20, 30]:
        for b in [1, 2, 3]:
            rows.append({"p_a": a, "p_b": b, "ROR": float(a + b)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# bars_per_level
# ---------------------------------------------------------------------------
def test_bars_per_level_returns_one_bar_per_level(grid_df):
    fig = charts.bars_per_level(grid_df, "p_a", "ROR", agg="mean")
    assert len(fig.data) == 1
    bar = fig.data[0]
    assert list(bar.x) == [10, 20, 30]
    # Mean of (a+1, a+2, a+3) = a + 2
    assert list(bar.y) == [12.0, 22.0, 32.0]
    # Mean agg should add error bars
    assert bar.error_y is not None and bar.error_y.array is not None


def test_bars_per_level_no_error_bars_for_non_mean(grid_df):
    fig = charts.bars_per_level(grid_df, "p_a", "ROR", agg="median")
    bar = fig.data[0]
    assert bar.error_y is None or bar.error_y.array is None


def test_bars_per_level_draws_baseline_line(grid_df):
    fig = charts.bars_per_level(
        grid_df, "p_a", "ROR", agg="mean", baseline_value=22.0
    )
    shapes = fig.layout.shapes or ()
    assert any(s.type == "line" for s in shapes), "expected baseline hline"


def test_bars_per_level_handles_missing_columns():
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    fig = charts.bars_per_level(df, "missing_param", "y")
    assert len(fig.data) == 0


# ---------------------------------------------------------------------------
# histogram_metric
# ---------------------------------------------------------------------------
def test_histogram_metric_bin_counts_match_numpy():
    df = pd.DataFrame({"ROR": np.arange(100, dtype=float)})
    fig = charts.histogram_metric(df, "ROR", bins=10)
    assert len(fig.data) == 1
    expected, _ = np.histogram(df["ROR"].to_numpy(), bins=10)
    assert list(fig.data[0].y) == list(expected)
    assert sum(fig.data[0].y) == len(df)


def test_histogram_metric_highlights_baseline_bin():
    df = pd.DataFrame({"ROR": np.arange(100, dtype=float)})
    # baseline = 25 -> falls in bin index 2 (edges every 9.9)
    fig = charts.histogram_metric(df, "ROR", baseline_value=25.0, bins=10)
    colors = list(fig.data[0].marker.color)
    assert colors.count(BASELINE_COLOR) == 1
    assert colors.count(SERIES_COLOR) == len(colors) - 1
    # Vertical baseline line should be drawn
    shapes = fig.layout.shapes or ()
    assert any(s.type == "line" for s in shapes)


def test_histogram_metric_no_highlight_without_baseline():
    df = pd.DataFrame({"ROR": np.arange(50, dtype=float)})
    fig = charts.histogram_metric(df, "ROR", bins=5)
    colors = list(fig.data[0].marker.color)
    assert all(c == SERIES_COLOR for c in colors)


def test_histogram_metric_baseline_outside_range_is_ignored():
    df = pd.DataFrame({"ROR": np.arange(10, dtype=float)})
    fig = charts.histogram_metric(df, "ROR", baseline_value=999.0, bins=5)
    colors = list(fig.data[0].marker.color)
    # Baseline is far outside the data range -> no bin highlighted
    assert all(c == SERIES_COLOR for c in colors)


def test_histogram_metric_handles_empty_or_missing():
    empty = pd.DataFrame({"ROR": [np.nan, np.nan]})
    assert len(charts.histogram_metric(empty, "ROR").data) == 0
    df = pd.DataFrame({"x": [1, 2]})
    assert len(charts.histogram_metric(df, "missing").data) == 0


# ---------------------------------------------------------------------------
# heatmap_two_params
# ---------------------------------------------------------------------------
def test_heatmap_two_params_pivot_shape(grid_df):
    fig = charts.heatmap_two_params(grid_df, "p_a", "p_b", "ROR")
    assert len(fig.data) == 1
    z = np.array(fig.data[0].z)
    assert z.shape == (3, 3)  # 3 levels of p_b x 3 levels of p_a
