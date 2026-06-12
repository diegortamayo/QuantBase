"""
Shared helpers for the fundamental feature modules.

Centralizes the three concerns every fundamental feature function needs:

  * column resolution - the unified per-ticker file is the outer merge of the
    income, cash-flow and balance-sheet statements (see utils.normalize.
    normalize_statements). Line items that appear on more than one statement are
    suffixed by the merge: '_x' is the left/earlier statement, '_y' the right one.
    Concretely:
        netIncome_x / depreciationAndAmortization_x -> income statement
        netIncome_y / depreciationAndAmortization_y -> cash-flow statement
        accountsReceivables_x / inventory_x         -> cash-flow statement
        accountsReceivables_y / inventory_y         -> balance sheet
    `canonical` hides this so feature code can ask for a semantic name and also
    keep working if a ticker is missing a statement (no collision -> plain name).

  * time-ordered quarterly lags and TTM aggregation - lags are aligned by an
    integer quarter index derived from fiscalYear + period, so a missing quarter
    produces NaN instead of silently borrowing the wrong neighbour.

  * NaN-safe division - never returns inf/0 for a zero, NaN or out-of-range
    denominator.
"""

import numpy as np
import pandas as pd


# Semantic name -> ordered list of candidate columns in the merged file.
# The first column that exists wins.
SUFFIX_CANDIDATES = {
    "netIncome": ("netIncome_x", "netIncome"),
    "depreciationAndAmortization": ("depreciationAndAmortization_x", "depreciationAndAmortization"),
    "accountsReceivables_bs": ("accountsReceivables_y", "accountsReceivables"),
    "inventory_bs": ("inventory_y", "inventory"),
    "accountsReceivables_cf": ("accountsReceivables_x", "accountsReceivables"),
    "inventory_cf": ("inventory_x", "inventory"),
}


def col(df: pd.DataFrame, *candidates: str) -> pd.Series:
    """
    Return the first existing candidate column as a numeric Series.

    Args:
        df: Source DataFrame.
        candidates: Column names tried in priority order.

    Returns:
        Numeric Series aligned to df.index; an all-NaN Series if none exist.
    """
    for name in candidates:
        if name in df.columns:
            return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype="float64")


def canonical(df: pd.DataFrame, name: str) -> pd.Series:
    """
    Resolve a semantic line-item name to a numeric Series, handling the
    income/cash/balance merge suffixes (see SUFFIX_CANDIDATES).

    Args:
        df: Source DataFrame.
        name: Semantic name (e.g. 'netIncome', 'inventory_bs', or any plain column).

    Returns:
        Numeric Series aligned to df.index.
    """
    return col(df, *SUFFIX_CANDIDATES.get(name, (name,)))


def quarter_index(df: pd.DataFrame) -> pd.Series:
    """
    Build an absolute integer quarter index from 'fiscalYear' and 'period'.

    Reads:  fiscalYear, period ('Q1'..'Q4').
    Returns: Series of int quarter ids (year*4 + quarter - 1); NaN where either
             field is missing/unparseable.
    """
    year = pd.to_numeric(df.get("fiscalYear"), errors="coerce")
    qnum = pd.to_numeric(
        df.get("period", pd.Series(index=df.index, dtype="object"))
        .astype(str)
        .str.extract(r"(\d+)", expand=False),
        errors="coerce",
    )
    return year * 4 + qnum - 1


def lag(df: pd.DataFrame, s: pd.Series, n: int) -> pd.Series:
    """
    Time-ordered quarterly lag: value from `n` quarters earlier, aligned by the
    absolute quarter index so gaps (missing quarters) yield NaN rather than the
    wrong row.

    Args:
        df: DataFrame providing fiscalYear/period for the quarter index.
        s: Series aligned to df.index (raw or derived).
        n: Number of quarters to look back.

    Returns:
        Series aligned to df.index with the lagged values.
    """
    qid = quarter_index(df)
    s = pd.to_numeric(s, errors="coerce")
    mapping = {int(q): v for q, v in zip(qid, s.values) if pd.notna(q)}
    out = [mapping.get(int(q) - n, np.nan) if pd.notna(q) else np.nan for q in qid]
    return pd.Series(out, index=df.index, dtype="float64")


def ttm(df: pd.DataFrame, s: pd.Series) -> pd.Series:
    """
    Trailing-twelve-month aggregate: sum of the current quarter and the three
    prior quarters. NaN unless all four quarters are present (NaN propagates).

    Args:
        df: DataFrame providing the quarter index.
        s: Flow Series to aggregate (aligned to df.index).

    Returns:
        TTM sum Series aligned to df.index.
    """
    s = pd.to_numeric(s, errors="coerce")
    return s + lag(df, s, 1) + lag(df, s, 2) + lag(df, s, 3)


def avg2(a: pd.Series, b: pd.Series) -> pd.Series:
    """Simple two-point average; NaN if either input is NaN."""
    return (a + b) / 2.0


def safe_div(num, den, min_abs: float = 0.0) -> pd.Series:
    """
    NaN-safe elementwise division.

    Returns NaN wherever the denominator is NaN or |denominator| <= min_abs
    (default: only an exact zero). NaN in the numerator propagates as usual.

    Args:
        num: Numerator (Series or scalar).
        den: Denominator (Series or scalar).
        min_abs: Denominators with absolute value at or below this are treated
            as invalid.

    Returns:
        Result Series of the division.
    """
    index = num.index if isinstance(num, pd.Series) else (
        den.index if isinstance(den, pd.Series) else None)
    if not isinstance(num, pd.Series):
        num = pd.Series(num, index=index)
    if not isinstance(den, pd.Series):
        den = pd.Series(den, index=index)
    num = pd.to_numeric(num, errors="coerce").astype("float64")
    den = pd.to_numeric(den, errors="coerce").astype("float64")
    bad = den.isna() | (den.abs() <= min_abs)
    return num.divide(den.where(~bad))


def safe_div_pos(num, den) -> pd.Series:
    """NaN-safe division that is also NaN whenever the denominator is <= 0."""
    den = pd.to_numeric(den, errors="coerce").astype("float64")
    return safe_div(num, den.where(den > 0))


def append(df: pd.DataFrame, new_columns: dict) -> pd.DataFrame:
    """
    Concatenate computed feature columns onto df, replacing any that already
    exist. Mirrors the concat/drop pattern used by the market feature modules.

    Args:
        df: Base DataFrame.
        new_columns: Mapping of feature name -> Series/array.

    Returns:
        DataFrame with the new feature columns appended.
    """
    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))
    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
