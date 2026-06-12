"""
Compute intrinsic-valuation inputs (DCF and DDM/GGM) from the unified quarterly
fundamental file.

The DCF block produces the reinvestment drivers (D&A and capex intensity, net
working capital and its change, reinvestment rate). The DDM/GGM block produces
dividends per share, the payout and retention ratios and the sustainable growth
rate. Depends on `nopat` and `roe` from profitability_features.

Reads (semantic line items): depreciationAndAmortization, revenue,
    capitalExpenditure, totalCurrentAssets, cashAndShortTermInvestments,
    totalCurrentLiabilities, shortTermDebt, commonDividendsPaid,
    weightedAverageShsOutDil, netIncome; and derived columns nopat, roe.

Produces: da_to_revenue, capex_to_revenue, nwc, delta_nwc, delta_nwc_to_revenue,
    reinvestment_rate, dps, payout_ratio, retention_ratio, sustainable_growth_rate.
"""

import pandas as pd

from ._fundamentals_helpers import canonical, append, safe_div, lag


def valuation_input_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate DCF and DDM/GGM valuation inputs.

    Args:
        df: Per-ticker fundamental DataFrame with profitability features already
            computed (needs 'nopat' and 'roe').

    Returns:
        DataFrame with valuation-input features appended.
    """
    da = canonical(df, "depreciationAndAmortization")
    revenue = canonical(df, "revenue")
    capex = canonical(df, "capitalExpenditure")
    tca = canonical(df, "totalCurrentAssets")
    cash_sti = canonical(df, "cashAndShortTermInvestments")
    tcl = canonical(df, "totalCurrentLiabilities")
    short_term_debt = canonical(df, "shortTermDebt")
    common_dividends = canonical(df, "commonDividendsPaid")
    shares_dil = canonical(df, "weightedAverageShsOutDil")
    net_income = canonical(df, "netIncome")
    nopat = canonical(df, "nopat")
    roe = canonical(df, "roe")

    new = {}

    # DCF inputs.
    new["daToRevenue"] = safe_div(da, revenue)
    new["capexToRevenue"] = safe_div(capex.abs(), revenue)

    nwc = tca - cash_sti - tcl + short_term_debt
    new["nwc"] = nwc
    delta_nwc = nwc - lag(df, nwc, 4)
    new["deltaNwc"] = delta_nwc
    new["deltaNwcToRevenue"] = safe_div(delta_nwc, revenue)
    # Reinvestment rate is undefined for non-positive NOPAT.
    new["reinvestmentRate"] = safe_div(capex.abs() - da + delta_nwc, nopat.where(nopat > 0))

    # DDM / GGM inputs.
    new["dps"] = safe_div(common_dividends.abs(), shares_dil)
    payout = safe_div(common_dividends.abs(), net_income.where(net_income > 0)).clip(0, 1)
    new["payoutRatio"] = payout
    new["retentionRatio"] = 1 - payout
    new["sustainableGrowthRate"] = roe * (1 - payout)

    return append(df, new)
