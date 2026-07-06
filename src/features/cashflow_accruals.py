"""
Compute cash-flow-quality and accrual/earnings-quality features from the unified
quarterly fundamental file.

Cash-flow-quality features compare cash generation against accounting earnings and
revenue. The accrual block builds net operating assets (NOA) and the balance-sheet
(Sloan 1996) and cash-flow accrual ratios, both scaled by average NOA between the
current quarter and the same quarter one year ago, plus a revenue-quality ratio.

Reads (semantic line items): operatingCashFlow, netIncome, ebitda, freeCashFlow,
    revenue, capitalExpenditure, depreciationAndAmortization_cf, changeInWorkingCapital,
    totalAssets, cashAndShortTermInvestments, totalInvestments, totalLiabilities,
    totalDebt, netCashProvidedByInvestingActivities, accountsReceivables_bs.

Produces: cfo_to_net_income, cfo_to_ebitda, fcf_margin, fcf_to_net_income,
    capex_intensity_rev, capex_intensity_da, owner_earnings, noa,
    bs_accruals_ratio, cf_accruals_ratio, revenue_quality.
"""

import pandas as pd

from ._fundamentals_helpers import canonical, append, safe_div, lag, avg2


def cashflow_accruals_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate cash-flow-quality and accrual features.

    Args:
        df: Per-ticker fundamental DataFrame, sorted by date.

    Returns:
        DataFrame with cash-flow-quality and accrual features appended.
    """
    operating_cf = canonical(df, "operatingCashFlow")
    net_income = canonical(df, "netIncome")
    ebitda = canonical(df, "ebitda")
    fcf = canonical(df, "freeCashFlow")
    revenue = canonical(df, "revenue")
    capex = canonical(df, "capitalExpenditure")
    # Cash-flow-statement D&A: the reported non-cash add-back, which is what the
    # owner-earnings and capex-vs-D&A comparisons are defined against.
    da = canonical(df, "depreciationAndAmortization_cf")
    change_wc = canonical(df, "changeInWorkingCapital")
    total_assets = canonical(df, "totalAssets")
    cash_sti = canonical(df, "cashAndShortTermInvestments")
    total_investments = canonical(df, "totalInvestments")
    total_liabilities = canonical(df, "totalLiabilities")
    total_debt = canonical(df, "totalDebt")
    cf_investing = canonical(df, "netCashProvidedByInvestingActivities")
    # Balance-sheet receivables (level); the cash-flow copy is a period change.
    ar_bs = canonical(df, "accountsReceivables_bs")

    new = {}

    # Cash-flow quality.
    new["cfoToNet_income"] = safe_div(operating_cf, net_income)
    new["cfoToEbitda"] = safe_div(operating_cf, ebitda)
    new["fcfMargin"] = safe_div(fcf, revenue)
    new["fcfToNetIncome"] = safe_div(fcf, net_income)
    new["capexIntensityRev"] = safe_div(capex.abs(), revenue)
    new["capexIntensityDa"] = safe_div(capex.abs(), da)
    # capitalExpenditure is reported as a negative outflow, so it is added directly.
    new["ownerEarnings"] = net_income + da + capex + change_wc

    # Net operating assets and accrual ratios.
    noa = (total_assets - cash_sti - total_investments) - (total_liabilities - total_debt)
    new["noa"] = noa
    noa_q4 = lag(df, noa, 4)
    avg_noa = avg2(noa, noa_q4)

    new["bsAccrualsRatio"] = safe_div(noa - noa_q4, avg_noa)
    new["cfAccrualsRatio"] = safe_div(net_income - operating_cf - cf_investing, avg_noa)
    new["revenueQuality"] = safe_div(ar_bs - lag(df, ar_bs, 4), revenue - lag(df, revenue, 4))

    return append(df, new)
