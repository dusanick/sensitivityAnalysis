# Sensitivity Analysis Dashboard

Streamlit app for analysing parameter sensitivity sweeps. Upload a CSV of runs and an optional baseline to visualise how parameter changes affect strategy metrics.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
.venv\Scripts\activate
streamlit run app\main.py
```

Or double-click `run.bat` on Windows.

## Features

- **Parameter Effect** — bar chart per metric grouped by parameter level (mean/median/min/max, ±1 std whiskers)
- **Histograms** — distribution of each metric across all runs; baseline bin highlighted
- **Summary Statistics** — table with Count, Min, Max, Median, Average, Baseline Value, % Delta to Average/Median, Baseline Percentile with color coding (amber/green/red)
- **Heatmap** — two-parameter interaction matrix for any metric
- **Raw Data** — browse and download filtered data as CSV
- **Robust CSV parsing** — auto-detects encoding and delimiter; handles `%`, currency prefixes, European/US number formats

## Sidebar

| Section | Controls |
|---------|----------|
| **Upload** | Runs CSV (one row per param combination), Baseline CSV (single row) |
| **Column roles** | Parameter prefix (`newStrat_` default), override parameter/metric classification |
| **Analysis** | Parameter to analyse, metrics to plot (default: ROR, MaxDD, Expectancy, ProfitFactor), bar aggregation method |
| **Histograms & Statistics** | Metrics for histograms/stats, bin count (5–50), percentile thresholds (lower/upper sliders for color coding) |

## CSV Format

**Runs CSV** — one row per parameter combination. Columns: `Test` (ID), `newStrat_*` (parameters), metric columns (numeric strings OK).

**Baseline CSV** — same schema, single row. Column names matched case-insensitively.

## Tests

```bash
.venv\Scripts\activate
python -m pytest tests/ -q
```

