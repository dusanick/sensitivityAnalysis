"""Plotly chart builders for the sensitivity dashboard."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .analytics import metric_by_param_level
from .config import BASELINE_COLOR, SERIES_COLOR


def bars_per_level(
    df: pd.DataFrame,
    param: str,
    metric: str,
    agg: str = "mean",
    baseline_value: float | None = None,
) -> go.Figure:
    """One bar per level of ``param`` with Y = aggregated ``metric``.

    ``agg`` is one of: 'mean', 'median', 'min', 'max'.
    Baseline is drawn as a horizontal dashed dark-red reference line.
    """
    fig = go.Figure()
    summary = metric_by_param_level(df, param, metric)
    if summary.empty or agg not in summary.columns:
        return fig

    err_y = None
    hover_std = ""
    if agg == "mean":
        err_y = dict(type="data", array=summary["std"].fillna(0).values, visible=True)
        hover_std = "<br>\u00b11 std=%{error_y.array:.4g}"

    fig.add_trace(
        go.Bar(
            x=summary["level"],
            y=summary[agg],
            marker_color=SERIES_COLOR,
            error_y=err_y,
            text=[
                f"{v:.3g}<br><span style='font-size:10px;color:#777'>n={c}</span>"
                for v, c in zip(summary[agg], summary["count"])
            ],
            textposition="outside",
            hovertemplate=(
                f"{param}=%{{x}}<br>{agg}({metric})=%{{y:.4g}}"
                f"{hover_std}<extra></extra>"
            ),
        )
    )
    if baseline_value is not None and not np.isnan(baseline_value):
        fig.add_hline(
            y=baseline_value,
            line_color=BASELINE_COLOR,
            line_dash="dash",
            annotation_text=f"baseline = {baseline_value:.4g}",
            annotation_position="top left",
        )
    fig.update_layout(
        title=f"{agg}({metric}) per {param}",
        xaxis_title=param,
        yaxis_title=f"{agg}({metric})",
        margin=dict(l=20, r=20, t=50, b=20),
        height=380,
        bargap=0.15,
    )
    fig.update_xaxes(type="category")
    return fig


def histogram_metric(
    df: pd.DataFrame,
    metric: str,
    baseline_value: float | None = None,
    bins: int = 10,
) -> go.Figure:
    """Histogram of ``metric`` across all runs in ``df``.

    X = metric value (``bins`` equal-width bins).
    Y = number of runs falling in each bin.
    The bin containing ``baseline_value`` is highlighted dark red.
    """
    fig = go.Figure()
    if metric not in df.columns:
        return fig
    values = df[metric].dropna().to_numpy()
    if values.size == 0:
        return fig

    counts, edges = np.histogram(values, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    colors = [SERIES_COLOR] * len(counts)
    baseline_bin: int | None = None
    if baseline_value is not None and not np.isnan(baseline_value):
        # np.digitize with right=False: returns 1..len(edges)-1 for values
        # inside; clip so baselines exactly at the right edge land in last bin.
        idx = int(np.digitize([baseline_value], edges, right=False)[0]) - 1
        if 0 <= idx < len(counts):
            colors[idx] = BASELINE_COLOR
            baseline_bin = idx

    bin_labels = [
        f"[{edges[i]:.3g}, {edges[i+1]:.3g}{']' if i == len(counts)-1 else ')'}"
        for i in range(len(counts))
    ]
    fig.add_trace(
        go.Bar(
            x=centers,
            y=counts,
            width=widths,
            marker_color=colors,
            customdata=bin_labels,
            hovertemplate=(
                f"{metric} bin=%{{customdata}}<br>count=%{{y}}<extra></extra>"
            ),
        )
    )
    if baseline_value is not None and not np.isnan(baseline_value):
        fig.add_vline(
            x=baseline_value,
            line_color=BASELINE_COLOR,
            line_dash="dash",
            annotation_text=f"baseline = {baseline_value:.4g}",
            annotation_position="top",
        )

    title = f"Distribution of {metric}  ({len(values)} runs, {bins} bins)"
    if baseline_bin is not None:
        title += f"  · baseline in bin {baseline_bin + 1}"
    fig.update_layout(
        title=title,
        xaxis_title=metric,
        yaxis_title="Count of runs",
        margin=dict(l=20, r=20, t=50, b=20),
        height=360,
        bargap=0.05,
        showlegend=False,
    )
    return fig


def heatmap_two_params(
    df: pd.DataFrame, param_x: str, param_y: str, metric: str
) -> go.Figure:
    """Mean ``metric`` across the cross of two parameters."""
    pivot = df.pivot_table(index=param_y, columns=param_x, values=metric, aggfunc="mean")
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdBu",
            colorbar=dict(title=metric),
            hovertemplate=f"{param_x}=%{{x}}<br>{param_y}=%{{y}}<br>{metric}=%{{z:.4g}}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Mean {metric}: {param_x} × {param_y}",
        xaxis_title=param_x,
        yaxis_title=param_y,
        margin=dict(l=20, r=20, t=50, b=20),
        height=420,
    )
    return fig
