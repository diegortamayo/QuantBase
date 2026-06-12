"""
Compute profitability and return-on-capital features from the unified quarterly
fundamental file.

Produces margins, the effective tax rate, NOPAT, invested capital, the TTM-based
return ratios (ROA/ROE/ROIC/ROTE), asset-turnover ratios and the Fama-French RMW
operating-profitability factor input. ROA/ROE/ROIC/ROTE and the turnover ratios use
TTM flows over the two-point average of the relevant stock between the current quarter
and the same quarter one year ago.

Reads (semantic line items): revenue, grossProfit, ebit, ebitda, netIncome,
    incomeBeforeTax, incomeTaxExpense, costOfRevenue,
    sellingGeneralAndAdministrativeExpenses, interestExpense, totalAssets,
    totalStockholdersEquity, totalDebt, cashAndShortTermInvestments,
    goodwillAndIntangibleAssets, propertyPlantEquipmentNet.

Produces: gross_margin, ebit_margin, ebitda_margin, net_margin, effective_tax_rate,
    nopat, invested_capital, roa, roe, roic, rote, asset_turnover,
    fixed_asset_turnover, operating_profitability_rmw.
"""

import pandas as pd

from ._fundamentals_helpers import canonical, append, safe_div, lag, ttm, avg2


def profitability_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate profitability and return-on-capital features.

    Args:
        df: Per-ticker fundamental DataFrame, sorted by date.

    Returns:
        DataFrame with profitability features appended.
    """
    revenue = canonical(df, "revenue")
    gross_profit = canonical(df, "grossProfit")
    ebit = canonical(df, "ebit")
    ebitda = canonical(df, "ebitda")
    net_income = canonical(df, "netIncome")
    income_before_tax = canonical(df, "incomeBeforeTax")
    tax_expense = canonical(df, "incomeTaxExpense")
    cost_of_revenue = canonical(df, "costOfRevenue")
    sga = canonical(df, "sellingGeneralAndAdministrativeExpenses")
    interest_expense = canonical(df, "interestExpense")
    total_assets = canonical(df, "totalAssets")
    equity = canonical(df, "totalStockholdersEquity")
    total_debt = canonical(df, "totalDebt")
    cash_sti = canonical(df, "cashAndShortTermInvestments")
    goodwill_intangibles = canonical(df, "goodwillAndIntangibleAssets")
    ppe = canonical(df, "propertyPlantEquipmentNet")

    new = {}

    # Margins.
    new["grossMargin"] = safe_div(gross_profit, revenue)
    new["ebitMargin"] = safe_div(ebit, revenue)
    new["ebitdaMargin"] = safe_div(ebitda, revenue)
    new["netMargin"] = safe_div(net_income, revenue)

    # Effective tax rate: undefined for non-positive pre-tax income, clipped to [0, 1].
    etr = safe_div(tax_expense, income_before_tax).where(income_before_tax > 0).clip(0, 1)
    new["effectiveTaxRate"] = etr

    # NOPAT and invested capital.
    nopat = ebit * (1 - etr)
    new["nopat"] = nopat
    invested_capital = equity + total_debt - cash_sti
    new["investedCapital"] = invested_capital

    # TTM flows and year-ago stock averages.
    ni_ttm = ttm(df, net_income)
    rev_ttm = ttm(df, revenue)
    nopat_ttm = ttm(df, nopat)

    avg_assets = avg2(total_assets, lag(df, total_assets, 4))
    avg_equity = avg2(equity, lag(df, equity, 4))
    avg_ic = avg2(invested_capital, lag(df, invested_capital, 4))
    tangible_equity = equity - goodwill_intangibles
    avg_tangible_equity = avg2(tangible_equity, lag(df, tangible_equity, 4))
    avg_ppe = avg2(ppe, lag(df, ppe, 4))

    new["roa"] = safe_div(ni_ttm, avg_assets)
    new["roe"] = safe_div(ni_ttm, avg_equity)
    new["roic"] = safe_div(nopat_ttm, avg_ic)
    new["rote"] = safe_div(ni_ttm, avg_tangible_equity)
    new["assetTurnover"] = safe_div(rev_ttm, avg_assets)
    new["fixedAssetTurnover"] = safe_div(rev_ttm, avg_ppe)

    # Fama-French RMW operating-profitability factor input.
    operating_profit = revenue - cost_of_revenue - sga - interest_expense
    new["operatingProfitabilityRmw"] = safe_div(operating_profit, equity)

    return append(df, new)
