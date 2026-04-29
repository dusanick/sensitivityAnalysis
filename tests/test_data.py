import io

import pandas as pd
import pytest

from app.data import (
    align_baseline_columns,
    classify_columns,
    load_csv,
    preselected_metrics,
    validate_baseline,
)


def _csv(text: str) -> io.StringIO:
    return io.StringIO(text)


def test_load_csv_parses_percent_and_currency():
    text = (
        "Test,Name,ROR,NetProfit,newStrat_x\n"
        "1,a,27.49%,AUD 1234,10\n"
        "2,b,-5.10%,AUD 2345,20\n"
    )
    df = load_csv(_csv(text))
    assert df["ROR"].dtype.kind == "f"
    assert df["NetProfit"].dtype.kind in {"f", "i"}
    assert df.loc[0, "ROR"] == pytest.approx(27.49)
    assert df.loc[1, "NetProfit"] == pytest.approx(2345)


def test_load_csv_keeps_unparseable_strings():
    df = load_csv(_csv("Test,Name\n1,foo\n2,bar\n"))
    assert not pd.api.types.is_numeric_dtype(df["Name"])


def test_classify_columns_uses_prefix_and_whitelist():
    df = load_csv(
        _csv(
            "Test,Name,ROR,MaxDD,Trades,newStrat_a,newStrat_b,custom\n"
            "1,a,1,2,3,10,100,7\n2,b,4,5,6,20,200,8\n"
        )
    )
    roles = classify_columns(df)
    assert roles.id_cols == ["Test"]
    assert "Name" in roles.meta_cols
    assert set(roles.param_cols) == {"newStrat_a", "newStrat_b"}
    # Whitelisted metrics first, then extras like 'custom'
    assert roles.metric_cols[:3] == ["ROR", "MaxDD", "Trades"]
    assert "custom" in roles.metric_cols


def test_preselected_metrics_preserves_whitelist_order():
    metrics = ["custom", "MaxDD", "ROR", "Trades"]
    out = preselected_metrics(metrics)
    assert out == ["ROR", "MaxDD", "Trades"]


def test_validate_baseline_detects_missing_columns():
    runs = pd.DataFrame({"a": [1], "b": [2]})
    base_ok = pd.DataFrame({"a": [1], "b": [2], "extra": [9]})
    base_bad = pd.DataFrame({"a": [1]})
    assert validate_baseline(runs, base_ok) is None
    assert "missing" in validate_baseline(runs, base_bad).lower()
    assert "no rows" in validate_baseline(runs, runs.head(0)).lower()


# ---------------------------------------------------------------------------
# Robust-format tolerance (parity with correlationMatrix data_loader)
# ---------------------------------------------------------------------------
def test_load_csv_handles_semicolon_delimiter():
    df = load_csv(_csv("Test;ROR\n1;10.5%\n2;-3.2%\n"))
    assert list(df.columns) == ["Test", "ROR"]
    assert df.loc[0, "ROR"] == pytest.approx(10.5)


def test_load_csv_handles_european_decimal_comma():
    # "1.234,56" (EU thousands+decimal) and "12,5" (decimal only)
    df = load_csv(_csv("Test,ROR\n1,\"1.234,56\"\n2,\"12,5\"\n"))
    assert df.loc[0, "ROR"] == pytest.approx(1234.56)
    assert df.loc[1, "ROR"] == pytest.approx(12.5)


def test_load_csv_handles_parenthesised_negatives():
    df = load_csv(_csv("Test,NetProfit\n1,(1234.50)\n2,500\n"))
    assert df.loc[0, "NetProfit"] == pytest.approx(-1234.50)
    assert df.loc[1, "NetProfit"] == pytest.approx(500)


def test_load_csv_strips_whitespace_inside_numbers_and_in_headers():
    text = (
        "  Test , NetProfit \n"
        "1, 1 234 567 \n"
        "2, 2 000 \n"
    )
    df = load_csv(_csv(text))
    assert list(df.columns) == ["Test", "NetProfit"]
    assert df.loc[0, "NetProfit"] == pytest.approx(1234567)


def test_load_csv_handles_utf8_bom():
    # UTF-8 BOM prefix -> utf-8-sig fallback
    raw = ("\ufeffTest,ROR\n1,5%\n").encode("utf-8")
    df = load_csv(io.BytesIO(raw))
    assert list(df.columns) == ["Test", "ROR"]
    assert df.loc[0, "ROR"] == pytest.approx(5.0)


def test_validate_baseline_is_case_insensitive():
    runs = pd.DataFrame({"Test": [1], "ROR": [1.0]})
    base = pd.DataFrame({"test": [1], "ror": [1.0]})
    assert validate_baseline(runs, base) is None


def test_align_baseline_columns_renames_to_runs_casing():
    runs = pd.DataFrame({"Test": [1], "ROR": [1.0]})
    base = pd.DataFrame({"test": [1], " ror ": [2.0], "extra": [9]})
    aligned = align_baseline_columns(runs, base)
    assert list(aligned.columns) == ["Test", "ROR", "extra"]
    assert aligned.loc[0, "ROR"] == 2.0
