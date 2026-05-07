"""Streamlit entry point for the Sensitivity Analysis dashboard."""
from __future__ import annotations

import io
import sys
from pathlib import Path

# Allow `streamlit run app/main.py` to import the `app` package even though
# Streamlit invokes this file as a top-level script, not a module.
_PKG_PARENT = Path(__file__).resolve().parent.parent
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

import pandas as pd
import streamlit as st

from app import charts
from app.analytics import summary_statistics
from app.config import DEFAULT_PARAM_PREFIX
from app.data import (
    align_baseline_columns,
    classify_columns,
    load_csv,
    preselected_metrics,
    validate_baseline,
)

st.set_page_config(
    page_title="Sensitivity Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Cached loaders
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _load(buf: bytes, name: str) -> tuple[pd.DataFrame, list[str]]:
    """Cache wrapper — keyed by file bytes so re-uploading the same file is free.
    Returns (dataframe, list_of_percentage_columns)."""
    df = load_csv(io.BytesIO(buf))
    pct_columns = df.attrs.get("pct_columns", [])
    return df, pct_columns


def _read_upload(uploaded) -> tuple[pd.DataFrame | None, list[str]]:
    if uploaded is None:
        return None, []
    df, pct_columns = _load(uploaded.getvalue(), uploaded.name)
    return df, pct_columns


# ---------------------------------------------------------------------------
# Sidebar — uploads & column roles
# ---------------------------------------------------------------------------
def sidebar(runs: pd.DataFrame | None) -> dict:
    st.sidebar.title("Sensitivity Analysis")

    runs_file = st.sidebar.file_uploader("Runs CSV", type=["csv"], key="runs_file")
    base_file = st.sidebar.file_uploader(
        "Baseline CSV (single row)", type=["csv"], key="base_file"
    )

    state: dict = {"runs_file": runs_file, "base_file": base_file}

    if runs is None or runs.empty:
        st.sidebar.info("Upload a runs CSV to begin.")
        return state

    st.sidebar.markdown("---")
    st.sidebar.subheader("Column roles")
    prefix = st.sidebar.text_input(
        "Parameter prefix (auto-detect)", value=DEFAULT_PARAM_PREFIX
    )
    roles = classify_columns(runs, param_prefix=prefix)
    default_metrics = preselected_metrics(roles.metric_cols)

    all_cols = [c for c in runs.columns if c not in roles.id_cols + roles.meta_cols]

    with st.sidebar.expander("Parameters", expanded=True):
        c1, c2 = st.columns(2)
        if c1.button("Select all", key="param_all"):
            st.session_state["_params_sel"] = all_cols
        if c2.button("Clear", key="param_clear"):
            st.session_state["_params_sel"] = []
        default_params = st.session_state.get("_params_sel", roles.param_cols)
        params = st.multiselect(
            "Mark columns that are PARAMETERS",
            options=all_cols,
            default=[c for c in default_params if c in all_cols],
            key="params_multi",
        )

    metric_options = [c for c in all_cols if c not in params]
    with st.sidebar.expander("Metrics", expanded=True):
        c1, c2 = st.columns(2)
        if c1.button("Select all", key="metric_all"):
            st.session_state["_metrics_sel"] = metric_options
        if c2.button("Clear", key="metric_clear"):
            st.session_state["_metrics_sel"] = []
        default_m = st.session_state.get("_metrics_sel", default_metrics)
        metrics = st.multiselect(
            "Mark columns that are METRICS",
            options=metric_options,
            default=[c for c in default_m if c in metric_options],
            key="metrics_multi",
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Analysis")

    selected_param = (
        st.sidebar.selectbox("Parameter to analyse", options=params)
        if params
        else None
    )
    _default_plot_metrics = ["ROR", "MaxDD", "Expectancy", "ProfitFactor"]
    _default_sel = [m for m in _default_plot_metrics if m in metrics]
    selected_metrics = (
        st.sidebar.multiselect(
            "Metrics to plot",
            options=metrics,
            default=_default_sel or metrics[: min(4, len(metrics))],
        )
        if metrics
        else []
    )

    agg = st.sidebar.selectbox(
        "Bar aggregation", options=["mean", "median", "min", "max"], index=0,
        help=(
            "Each bar shows this aggregate of the metric across all runs that "
            "share the parameter level. Mean adds ±1 std error bars."
        ),
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Histograms & Statistics")
    hist_metrics = (
        st.sidebar.multiselect(
            "Metrics for histograms",
            options=metrics,
            default=selected_metrics,
            key="hist_metrics_multi",
            help="Each metric gets its own histogram in the Histograms tab.",
        )
        if metrics
        else []
    )
    hist_bins = st.sidebar.slider(
        "Histogram bins", min_value=5, max_value=50, value=10, step=1
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Summary Statistics")
    pct_low = st.sidebar.slider(
        "Lower percentile threshold",
        min_value=0.0, max_value=1.0, value=0.20, step=0.05,
        help="Below this → amber (weak baseline).",
    )
    pct_high = st.sidebar.slider(
        "Upper percentile threshold",
        min_value=0.0, max_value=1.0, value=0.70, step=0.05,
        help="At or above this → red (over-optimized).",
    )

    state.update(
        roles=roles,
        params=params,
        metrics=metrics,
        selected_param=selected_param,
        selected_metrics=selected_metrics,
        agg=agg,
        hist_metrics=hist_metrics,
        hist_bins=hist_bins,
        pct_low=pct_low,
        pct_high=pct_high,
    )
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_stat_cell(val, row_name: str, is_pct_col: bool = False) -> str:
    """Format a summary statistics cell value based on its row context.

    - Count: integer
    - Min/Max/Median/Average/Baseline Value: with % if column is a percentage,
      otherwise plain number
    - % Delta to Average/% Delta to Median: always as percentage (val*100 + %)
    - Baseline Percentile: always as percentage (val*100 + %)
    """
    if pd.isna(val):
        return "N/A"
    if row_name == "Count":
        return f"{int(val):,}"
    if row_name in ("% Delta to Average", "% Delta to Median", "Baseline Percentile"):
        return f"{val:.2%}"
    # Min, Max, Median, Average, Baseline Value
    if isinstance(val, float):
        if is_pct_col:
            return f"{val:.2f}%"
        return f"{val:,.2f}"
    return f"{val:,.0f}"


def _filter_other_params(
    runs: pd.DataFrame, params: list[str], selected_param: str
) -> tuple[pd.DataFrame, dict]:
    """Render filter sliders/multiselects for the OTHER parameters."""
    df = runs
    chosen = {}
    others = [p for p in params if p != selected_param]
    if not others:
        return df, chosen
    with st.expander("Filter other parameters", expanded=False):
        cols = st.columns(min(4, len(others)))
        for i, p in enumerate(others):
            with cols[i % len(cols)]:
                values = sorted(runs[p].dropna().unique().tolist())
                pick = st.multiselect(p, options=values, default=values, key=f"flt_{p}")
                chosen[p] = pick
                # Empty selection = exclude every row for that parameter
                # (since every run carries a value). This produces an empty df
                # rather than silently keeping all rows.
                df = df[df[p].isin(pick)]
    return df, chosen


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    runs_raw, _ = _read_upload(st.session_state.get("runs_file"))
    state = sidebar(runs_raw)

    runs, pct_columns = _read_upload(state.get("runs_file"))
    baseline_df, _ = _read_upload(state.get("base_file"))

    st.title("Parameter Sensitivity Dashboard")
    st.caption(
        "Upload a sweep CSV and a baseline CSV. Stable lines = robust strategy. "
        "Cliff edges = fragile."
    )

    if runs is None:
        st.info("Awaiting upload.")
        return

    baseline_row: pd.Series | None = None
    if baseline_df is not None:
        baseline_df = align_baseline_columns(runs, baseline_df)
        err = validate_baseline(runs, baseline_df)
        if err:
            st.error(err)
        else:
            if len(baseline_df) > 1:
                st.warning(
                    f"Baseline has {len(baseline_df)} rows; using the first."
                )
            baseline_row = baseline_df.iloc[0]

    params: list[str] = state.get("params", [])
    metrics: list[str] = state.get("metrics", [])
    selected_param: str | None = state.get("selected_param")
    selected_metrics: list[str] = state.get("selected_metrics", [])
    agg: str = state.get("agg", "mean")
    hist_metrics: list[str] = state.get("hist_metrics", [])
    hist_bins: int = state.get("hist_bins", 10)

    if not params or not metrics:
        st.info("Use the sidebar to mark which columns are parameters and metrics.")
        return
    if selected_param is None or not selected_metrics:
        st.info("Pick a parameter and at least one metric in the sidebar.")
        return

    # Apply user filters on the OTHER parameters first. This df is shared by
    # the heatmap (which handles its own aggregation).
    base_df, _ = _filter_other_params(runs, params, selected_param)

    if base_df.empty:
        st.warning(
            "No rows match the current 'Filter other parameters' selection. "
            "Add at least one value back per parameter to see results."
        )
        return

    plot_df = base_df
    plot_baseline = baseline_row

    # Status banner so the user can see what's actually happening.
    base_status = "uploaded" if baseline_row is not None else "—"
    st.info(
        f"**Rows in view:** {len(plot_df)}  ·  **Baseline:** {base_status}"
    )

    tab_effect, tab_hist, tab_summary, tab_heatmap, tab_data = st.tabs(
        ["Parameter Effect", "Histograms", "Summary Statistics", "Heatmap", "Raw Data"]
    )

    # --- Parameter Effect ---
    with tab_effect:
        st.subheader(f"Effect of `{selected_param}` on selected metrics")
        std_note = " · grey whiskers = **±1 std**" if agg == "mean" else ""
        st.caption(
            f"Rows: **{len(plot_df)}** · Bar agg: **{agg}**{std_note} · "
            "`n=` shows runs aggregated per bar"
        )
        for m in selected_metrics:
            st.plotly_chart(
                charts.bars_per_level(
                    plot_df, selected_param, m, agg=agg, baseline_value=None,
                ),
                use_container_width=True,
            )

    # --- Histograms ---
    with tab_hist:
        st.subheader("Metric distributions across runs")
        st.caption(
            f"Rows: **{len(base_df)}** · Bins: **{hist_bins}** · "
            "Bin containing the baseline is highlighted dark red."
        )
        if not hist_metrics:
            st.info(
                "Pick at least one metric in the sidebar (Histograms section)."
            )
        else:
            for m in hist_metrics:
                base_val = (
                    float(baseline_row[m])
                    if baseline_row is not None and m in baseline_row.index
                    and pd.notna(baseline_row[m])
                    else None
                )
                st.plotly_chart(
                    charts.histogram_metric(
                        base_df, m, baseline_value=base_val, bins=hist_bins,
                    ),
                    use_container_width=True,
                )

    # --- Summary Statistics ---
    with tab_summary:
        st.subheader("Summary Statistics")
        pct_low: float = state.get("pct_low", 0.20)
        pct_high: float = state.get("pct_high", 0.70)
        if not hist_metrics:
            st.info(
                "Pick at least one metric in the sidebar (Histograms section)."
            )
        else:
            stats_df = summary_statistics(base_df, hist_metrics, baseline_row)
            st.caption(
                f"Rows: **{len(base_df)}** · Metrics: **{len(hist_metrics)}** · "
                f"Percentile thresholds: amber < {pct_low:.0%}, "
                f"green {pct_low:.0%}–{pct_high:.0%}, red ≥ {pct_high:.0%}"
            )

            def _color_percentile(val):
                """Return CSS for percentile cell coloring."""
                if pd.isna(val):
                    return ""
                if val < pct_low:
                    return "background-color: #FFF9C4; color: #F57F17"
                if val >= pct_high:
                    return "background-color: #FCE4EC; color: #C00000"
                return "background-color: #E2EFDA; color: #2E7D32"

            # Apply row-aware formatting to each cell
            pct_cols = set(pct_columns)
            formatted_df = stats_df.astype(object).copy()
            for row_name in formatted_df.index:
                for col in formatted_df.columns:
                    formatted_df.at[row_name, col] = _fmt_stat_cell(
                        stats_df.at[row_name, col], row_name,
                        is_pct_col=(col in pct_cols),
                    )

            styled = formatted_df.style.apply(
                lambda row: [
                    _color_percentile(stats_df.at[row.name, col])
                    if row.name == "Baseline Percentile"
                    else ""
                    for col in row.index
                ],
                axis=1,
            )
            st.dataframe(styled, use_container_width=True)

    # --- Heatmap ---
    with tab_heatmap:
        st.subheader("Two-parameter interaction heatmap")
        if len(params) < 2:
            st.info("Need at least 2 parameters to draw a heatmap.")
        else:
            c1, c2, c3 = st.columns(3)
            px_p = c1.selectbox("X parameter", options=params, index=0, key="hm_x")
            py_options = [p for p in params if p != px_p]
            py_p = c2.selectbox("Y parameter", options=py_options, index=0, key="hm_y")
            hm_metric = c3.selectbox(
                "Metric", options=selected_metrics, key="hm_metric"
            )
            st.plotly_chart(
                charts.heatmap_two_params(base_df, px_p, py_p, hm_metric),
                use_container_width=True,
            )

    # --- Raw data ---
    with tab_data:
        st.subheader("Filtered data")
        st.dataframe(base_df, use_container_width=True, height=500)
        st.download_button(
            "Download filtered CSV",
            data=base_df.to_csv(index=False).encode("utf-8"),
            file_name="sensitivity_filtered.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
