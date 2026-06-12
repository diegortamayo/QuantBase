"""
Compute leverage and liquidity features from the unified quarterly fundamental file.

Leverage ratios mix point-in-time balance-sheet stocks with TTM income/coverage
flows; liquidity ratios are point-in-time, and the activity ratios (DSO/DIO/DPO,
combined into the cash-conversion cycle) annualize the current quarter using
DAYS_IN_QUARTER.

Reads (semantic line items): netDebt, ebitda, totalStockholdersEquity, totalDebt,
    totalAssets, ebit, interestExpense, totalCurrentAssets, totalCurrentLiabilities,
    inventory_bs, cashAndCashEquivalents, netReceivables, revenue, costOfRevenue,
    accountPayables, operatingCashFlow.

Produces: net_debt_to_ebitda, net_debt_to_equity, debt_to_assets, debt_to_capital,
    interest_coverage, equity_multiplier, current_ratio, quick_ratio, cash_ratio,
    dso, dio, dpo, ccc, cfo_to_current_liabilities.
"""

import pandas as pd

from config.features_config import DAYS_IN_QUARTER

from ._fundamentals_helpers import canonical, append, safe_div, ttm


def leverage_liquidity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate leverage and liquidity features.

    Args:
        df: Per-ticker fundamental DataFrame, sorted by date.

    Returns:
        DataFrame with leverage and liquidity features appended.
    """
    net_debt = canonical(df, "netDebt")
    ebitda = canonical(df, "ebitda")
    equity = canonical(df, "totalStockholdersEquity")
    total_debt = canonical(df, "totalDebt")
    total_assets = canonical(df, "totalAssets")
    ebit = canonical(df, "ebit")
    interest_expense = canonical(df, "interestExpense")
    tca = canonical(df, "totalCurrentAssets")
    tcl = canonical(df, "totalCurrentLiabilities")
    inventory_bs = canonical(df, "inventory_bs")
    cash = canonical(df, "cashAndCashEquivalents")
    net_receivables = canonical(df, "netReceivables")
    revenue = canonical(df, "revenue")
    cost_of_revenue = canonical(df, "costOfRevenue")
    account_payables = canonical(df, "accountPayables")
    operating_cf = canonical(df, "operatingCashFlow")

    new = {}

    # Leverage.
    new["netDebtToEbitda"] = safe_div(net_debt, ttm(df, ebitda))
    new["netDebtToEquity"] = safe_div(net_debt, equity)
    new["debtToAssets"] = safe_div(total_debt, total_assets)
    new["debtToCapital"] = safe_div(total_debt, total_debt + equity)
    # Interest coverage on a TTM basis; NaN when there is no interest expense.
    new["interestCoverage"] = safe_div(ttm(df, ebit), ttm(df, interest_expense))
    new["equityMultiplier"] = safe_div(total_assets, equity)
    new["interestCoverageProxy"] = safe_div(operating_cf, total_debt)

    # Liquidity.
    new["currentRatio"] = safe_div(tca, tcl)
    new["quickRatio"] = safe_div(tca - inventory_bs, tcl)
    new["cashRatio"] = safe_div(cash, tcl)

    # Activity ratios: annualize the current quarter (DAYS_IN_QUARTER per quarter).
    new["dso"] = safe_div(net_receivables, revenue / DAYS_IN_QUARTER)
    new["dio"] = safe_div(inventory_bs, cost_of_revenue / DAYS_IN_QUARTER)
    new["dpo"] = safe_div(account_payables, cost_of_revenue / DAYS_IN_QUARTER)
    new["ccc"] = new["dso"] + new["dio"] - new["dpo"]

    new["cfoToCurrentLiabilities"] = safe_div(operating_cf, tcl)

    return append(df, new)
