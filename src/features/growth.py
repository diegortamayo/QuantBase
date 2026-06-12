"""
Compute growth-rate features from the unified quarterly fundamental file.

For each base line item in GROWTH_BASE_COLUMNS the module produces a quarter-on-quarter
rate (vs one quarter ago), a year-on-year rate (vs the same quarter one year ago) and
TTM-CAGR variants over the horizons in CAGR_HORIZONS (which need 12 / 20 quarters of
history and are NaN when that history or a non-positive base is missing). Also produces
the asset-growth (CMA) factor input.

Reads (semantic line items): the columns listed in GROWTH_BASE_COLUMNS
    (revenue, grossProfit, ebit, netIncome, epsDiluted, capitalExpenditure,
    totalStockholdersEquity) and totalAssets.

Produces, for each base column X: X_qoq, X_yoy, X_cagr_3y, X_cagr_5y; plus
    asset_growth_yoy.
"""

import pandas as pd

from config.features_config import GROWTH_BASE_COLUMNS, CAGR_HORIZONS

from ._fundamentals_helpers import canonical, append, safe_div, lag


def _cagr(x: pd.Series, x_lag: pd.Series, years: int) -> pd.Series:
    """Annualized growth (x / x_lag)^(1/years) - 1; NaN unless the ratio is positive."""
    ratio = safe_div(x, x_lag)
    ratio = ratio.where(ratio > 0)
    return ratio ** (1.0 / years) - 1


def growth_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate QoQ, YoY and TTM-CAGR growth features plus the asset-growth factor.

    Args:
        df: Per-ticker fundamental DataFrame, sorted by date.

    Returns:
        DataFrame with growth features appended.
    """
    new = {}

    for name in GROWTH_BASE_COLUMNS:
        x = canonical(df, name)
        x_q1 = lag(df, x, 1)
        x_q4 = lag(df, x, 4)
        new[f"{name}Qoq"] = safe_div(x - x_q1, x_q1.abs())
        new[f"{name}Yoy"] = safe_div(x - x_q4, x_q4.abs())
        for label, (quarter_lag, years) in CAGR_HORIZONS.items():
            new[f"{name}_{label}"] = _cagr(x, lag(df, x, quarter_lag), years)

    total_assets = canonical(df, "totalAssets")
    new["assetGrowthYoy"] = safe_div(total_assets, lag(df, total_assets, 4)) - 1

    return append(df, new)
