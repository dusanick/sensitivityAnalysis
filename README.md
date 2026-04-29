# Sensitivity Analysis Dashboard

Interactive Streamlit dashboard for exploring how parameter variations from a
RealTest-style sensitivity sweep influence strategy metrics. Inspired by the
`Param Sensitivity` tab in `Robustness_Testing_Templates_V1.xlsx` and extended
with per-parameter bar charts, two-parameter heatmaps and metric-distribution
histograms vs a baseline run.

## Features

| Feature | Description |
|---------|-------------|
| **Parameter Effect** | One bar per level of the chosen parameter, Y = mean / median / min / max of metric across all runs sharing that level. Mean shows ±1 std whiskers. |
| **Histograms** | Distribution of each selected metric across all (filtered) runs; bin containing the baseline value highlighted dark red. |
| **Heatmap** | Mean of any metric across the cross of two parameters. |
| **Raw Data** | Browse and download the filtered runs frame as CSV. |
| **Robust CSV upload** | Auto-detects encoding (utf-8 / utf-8-sig / cp1252 / latin-1) and delimiter (`,` `;` tab `\|`). Parses `27.49%`, `(1234.50)`, `AUD 1,234`, `1.234,56` (EU) and `1 234 567`. |
| **Flexible baseline** | Baseline column names matched case-insensitively and aligned to the runs frame. |
| **Configurable column roles** | Smart defaults (`newStrat_*` → parameter, common stat names → metric) are overridable via checkboxes. |
| **Other-parameter filter** | Per-parameter multiselects to slice the dataset before analysis. |

## Project Structure

```
sensitivityAnalysis/
├── app/
│   ├── main.py          # Streamlit entry-point + sidebar / tabs
│   ├── data.py          # CSV I/O, numeric coercion, column classification
│   ├── analytics.py     # Per-level aggregation, baseline delta
│   ├── charts.py        # Plotly chart builders (bars / histogram / heatmap)
│   └── config.py        # Default whitelists, colours, prefixes
├── tests/
│   ├── test_data.py
│   ├── test_analytics.py
│   └── test_charts.py
├── requirements.txt
├── run.bat              # Windows one-click launcher
└── README.md
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Usage

```powershell
streamlit run app\main.py
```

Or double-click `run.bat`.

Then in the sidebar:

1. Upload your **runs CSV** (one row per parameter combination).
2. Upload your **baseline CSV** (single-row reference run).
3. Use the **Column roles** checkboxes to confirm which columns are
   parameters and which are metrics.
4. Pick a parameter and one or more metrics to analyse.
5. (Optional) Pick metrics + bin count for the Histograms tab.

### Sidebar Controls

| Control | Default | Description |
|---------|---------|-------------|
| Runs CSV | — | Sweep file, one row per parameter combination |
| Baseline CSV | — | Single-row reference run |
| Parameter prefix | `newStrat_` | Auto-classifies columns as parameters |
| Parameters / Metrics | auto | Override the auto-classification |
| Parameter to analyse | first | Drives the Parameter Effect tab |
| Metrics to plot | first 3 | Bar charts, one per metric |
| Bar aggregation | mean | mean (±1 std) / median / min / max |
| Histogram metrics | = analysis metrics | Independent metric set for the Histograms tab |
| Histogram bins | 10 | 5–50 |

### CSV Format

Runs CSV — one row per parameter combination, e.g. a 5×5×5×5 full-factorial
sweep produces 625 rows. Required columns:

| Column | Example | Notes |
|--------|---------|-------|
| `Test` | `1` | Run identifier (or first column) |
| `newStrat_*` | `10` | Parameter columns (any prefix is configurable) |
| Metric columns | `27.49%`, `AUD 1234`, `(500)` | Numeric strings tolerated |

Baseline CSV — same schema, single row. Column casing/whitespace need not
match the runs file exactly.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

25 tests covering data loading, robust numeric/encoding parsing, column
classification, analytics aggregation and chart construction.

