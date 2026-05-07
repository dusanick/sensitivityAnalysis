"""CSV loading, cleaning and column classification."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .config import DEFAULT_METRICS, DEFAULT_PARAM_PREFIX, META_COLUMNS

# Match leading/trailing junk we want to strip before numeric coercion.
# Examples: "27.49%", "-62.97%", "(5.28%)", "AUD 53589219", "$1,234.50",
# " 1 234,5 ", "1.234,56" (European), "1,234.56" (US)
_PERCENT_RE = re.compile(r"%\s*$")
_CURRENCY_PREFIX_RE = re.compile(r"^[A-Za-z$€£¥]{1,4}\s*")
_TRAILING_CURRENCY_RE = re.compile(r"\s*[A-Za-z$€£¥]{1,4}\s*$")
_PAREN_NEG_RE = re.compile(r"^\((.*)\)$")
# Detects pure whitespace between digits (e.g. "1 234 567")
_WS_BETWEEN_DIGITS_RE = re.compile(r"(?<=\d)\s+(?=\d)")

# Encodings to try, in order. utf-8-sig handles the common Excel BOM.
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


# ---------------------------------------------------------------------------
# Numeric coercion
# ---------------------------------------------------------------------------
def _strip_thousands_and_decimal(text: str) -> str:
    """Normalise a single numeric string to use '.' as decimal separator and
    no thousands separator. Handles both ``1,234.56`` and ``1.234,56`` styles
    by inspecting which separator appears last."""
    has_comma = "," in text
    has_dot = "." in text
    if has_comma and has_dot:
        # Whichever appears LAST is the decimal separator.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif has_comma:
        # Comma alone: treat as decimal only when followed by 1-2 digits and
        # there is exactly one comma (e.g. "1,5" or "12,34"). Otherwise it's
        # a thousands separator (e.g. "1,234" -> "1234").
        parts = text.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            text = parts[0] + "." + parts[1]
        else:
            text = text.replace(",", "")
    return text


def _coerce_series(s: pd.Series) -> tuple[pd.Series, bool]:
    """Best-effort convert a series of strings like '27.49%', '(5.28%)' or
    'AUD 1,234' to floats. Leaves the column untouched if conversion produces
    fewer than 50% valid values.

    Returns (converted_series, is_percentage).
    """
    if pd.api.types.is_numeric_dtype(s):
        return s, False

    cleaned = s.astype("string").str.strip()

    # Detect if majority of non-null values contain a '%' sign
    non_null_mask = cleaned.notna() & (cleaned != "<NA>")
    non_null_count = non_null_mask.sum()
    has_pct = cleaned[non_null_mask].str.contains("%", na=False).sum()
    is_pct = non_null_count > 0 and has_pct / non_null_count >= 0.5

    # Parenthesised negatives -> prefix with '-'
    cleaned = cleaned.str.replace(_PAREN_NEG_RE, r"-\1", regex=True)
    cleaned = cleaned.str.replace(_CURRENCY_PREFIX_RE, "", regex=True)
    cleaned = cleaned.str.replace(_TRAILING_CURRENCY_RE, "", regex=True)
    cleaned = cleaned.str.replace(_PERCENT_RE, "", regex=True)
    cleaned = cleaned.str.replace(_WS_BETWEEN_DIGITS_RE, "", regex=True)
    cleaned = cleaned.str.strip()
    cleaned = cleaned.map(
        lambda v: _strip_thousands_and_decimal(v) if isinstance(v, str) else v
    )

    converted = pd.to_numeric(cleaned, errors="coerce")
    non_null = s.notna().sum()
    if non_null and converted.notna().sum() / non_null >= 0.5:
        return converted, is_pct
    return s, False


# ---------------------------------------------------------------------------
# Flexible CSV reader
# ---------------------------------------------------------------------------
def _read_csv_flexible(file: str | io.IOBase | bytes) -> pd.DataFrame:
    """Read a CSV trying several encodings and auto-detecting the delimiter.

    Accepts a path, a bytes payload or a file-like object (re-seeked between
    attempts). Falls back to latin-1 if every other encoding fails.
    """
    if isinstance(file, (bytes, bytearray)):
        file = io.BytesIO(file)

    last_err: Exception | None = None
    for enc in _ENCODINGS:
        try:
            if hasattr(file, "seek"):
                file.seek(0)
            # sep=None + engine='python' -> sniff ',', ';', tab, '|'
            return pd.read_csv(file, encoding=enc, sep=None, engine="python")
        except (UnicodeDecodeError, UnicodeError) as exc:
            last_err = exc
            continue
        except pd.errors.ParserError as exc:
            # Sniffer failed for this encoding; try next.
            last_err = exc
            continue

    # Last resort
    if hasattr(file, "seek"):
        file.seek(0)
    try:
        return pd.read_csv(file, encoding="latin-1")
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Could not parse CSV: {exc}") from last_err


def load_csv(file: str | io.IOBase | bytes) -> pd.DataFrame:
    """Read a sensitivity-analysis CSV and coerce numeric-looking columns.

    Tolerates:
      * different encodings (utf-8 / utf-8-sig / cp1252 / latin-1)
      * different delimiters (',', ';', tab, '|')
      * percentage strings, currency prefixes, parenthesised negatives,
        US (1,234.56) and European (1.234,56) thousand/decimal separators,
        whitespace inside numbers
      * leading / trailing whitespace in column headers
    """
    df = _read_csv_flexible(file)
    df.columns = [str(c).strip() for c in df.columns]
    pct_columns: list[str] = []
    for col in df.columns:
        df[col], is_pct = _coerce_series(df[col])
        if is_pct:
            pct_columns.append(col)
    df.attrs["pct_columns"] = pct_columns
    return df


@dataclass(frozen=True)
class ColumnRoles:
    """Auto-classified column roles. The UI uses these as checkbox defaults
    but the user is free to override them."""

    id_cols: list[str]
    meta_cols: list[str]
    param_cols: list[str]
    metric_cols: list[str]


def classify_columns(
    df: pd.DataFrame,
    param_prefix: str = DEFAULT_PARAM_PREFIX,
    metric_whitelist: Iterable[str] = DEFAULT_METRICS,
) -> ColumnRoles:
    """Heuristically split columns into id / meta / parameter / metric buckets.

    Rules:
      * `Test` (or first column if missing) → id.
      * Anything in META_COLUMNS → meta.
      * Anything starting with ``param_prefix`` → parameter.
      * Numeric columns matching ``metric_whitelist`` → metric (preselected).
      * Remaining numeric columns → metric (available, not preselected by
        caller — the UI separates "preselected" vs "available").
    """
    cols = list(df.columns)
    metric_set = {m.lower() for m in metric_whitelist}

    id_cols: list[str] = []
    if "Test" in cols:
        id_cols.append("Test")
    elif cols:
        id_cols.append(cols[0])

    meta_cols = [c for c in cols if c in META_COLUMNS and c not in id_cols]
    param_cols = [c for c in cols if c.startswith(param_prefix) and c not in id_cols]

    used = set(id_cols) | set(meta_cols) | set(param_cols)
    metric_cols = [
        c
        for c in cols
        if c not in used
        and pd.api.types.is_numeric_dtype(df[c])
        and c.lower() in metric_set
    ]
    # Append remaining numeric, non-classified columns so the user sees them
    # in the metric checkbox list (just not preselected).
    extras = [
        c
        for c in cols
        if c not in used
        and c not in metric_cols
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    metric_cols.extend(extras)

    return ColumnRoles(id_cols, meta_cols, param_cols, metric_cols)


def preselected_metrics(
    metric_cols: Iterable[str],
    whitelist: Iterable[str] = DEFAULT_METRICS,
) -> list[str]:
    """Return the subset of metric_cols that match the default whitelist
    (case-insensitive), preserving whitelist order."""
    available = {c.lower(): c for c in metric_cols}
    return [available[m.lower()] for m in whitelist if m.lower() in available]


def align_baseline_columns(
    runs: pd.DataFrame, baseline: pd.DataFrame
) -> pd.DataFrame:
    """Rename baseline columns to match the runs frame's casing/whitespace.

    Useful when the baseline CSV was exported separately and has slightly
    different headers (e.g. lowercased). Columns absent from runs are kept
    as-is.
    """
    runs_lookup = {str(c).strip().lower(): c for c in runs.columns}
    rename: dict[str, str] = {}
    for c in baseline.columns:
        key = str(c).strip().lower()
        target = runs_lookup.get(key)
        if target is not None and c != target:
            rename[c] = target
    return baseline.rename(columns=rename) if rename else baseline


def validate_baseline(runs: pd.DataFrame, baseline: pd.DataFrame) -> str | None:
    """Return an error message if the baseline schema is incompatible with
    the runs frame, else None. Matching is case-insensitive and tolerant of
    surrounding whitespace; extra baseline columns are tolerated."""
    if len(baseline) == 0:
        return "Baseline file contains no rows."
    base_lookup = {str(c).strip().lower() for c in baseline.columns}
    missing = [
        c for c in runs.columns if str(c).strip().lower() not in base_lookup
    ]
    if missing:
        return f"Baseline is missing required columns: {', '.join(missing[:5])}"
    return None
