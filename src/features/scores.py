"""
Compute composite financial-health / earnings-manipulation scores from the unified
quarterly fundamental file.

Includes the Piotroski F-Score (nine binary signals plus their sum), the Altman Z''
score (emerging-markets / non-manufacturing variant) and its components, the Beneish
M-Score (eight index components plus the total) and the financial-statement component
of the Greenblatt Magic Formula ROIC.

Depends on derived columns produced by earlier modules: roa, debt_to_assets,
current_ratio, gross_margin, asset_turnover, cfo_to_net_income, nwc.

Reads (semantic line items): operatingCashFlow, weightedAverageShsOutDil,
    totalCurrentAssets, totalCurrentLiabilities, totalAssets, retainedEarnings, ebit,
    totalStockholdersEquity, totalLiabilities, netReceivables, revenue, grossProfit,
    propertyPlantEquipmentNet, depreciationAndAmortization,
    sellingGeneralAndAdministrativeExpenses, totalDebt, netIncome,
    propertyPlantEquipmentNet.

Produces: f_roa, f_delta_roa, f_cfo, f_accruals, f_delta_leverage, f_delta_liquidity,
    f_no_dilution, f_delta_gross_margin, f_delta_asset_turnover, f_score_total;
    z_wc_ta, z_re_ta, z_ebit_ta, z_bve_bvl, altman_z_score; beneish_dsri, beneish_gmi,
    beneish_aqi, beneish_sgi, beneish_depi, beneish_sgai, beneish_lvgi, beneish_tata,
    m_score_total; greenblatt_roic.
"""

import pandas as pd

from ._fundamentals_helpers import canonical, append, safe_div, lag


def score_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate Piotroski, Altman, Beneish and Greenblatt (FS) composite scores.

    Args:
        df: Per-ticker fundamental DataFrame with profitability, leverage/liquidity,
            cash-flow and valuation-input features already computed.

    Returns:
        DataFrame with composite-score features appended.
    """
    # Raw line items.
    operating_cf = canonical(df, "operatingCashFlow")
    shares_dil = canonical(df, "weightedAverageShsOutDil")
    tca = canonical(df, "totalCurrentAssets")
    tcl = canonical(df, "totalCurrentLiabilities")
    total_assets = canonical(df, "totalAssets")
    retained_earnings = canonical(df, "retainedEarnings")
    ebit = canonical(df, "ebit")
    equity = canonical(df, "totalStockholdersEquity")
    total_liabilities = canonical(df, "totalLiabilities")
    net_receivables = canonical(df, "netReceivables")
    revenue = canonical(df, "revenue")
    gross_profit = canonical(df, "grossProfit")
    ppe = canonical(df, "propertyPlantEquipmentNet")
    da = canonical(df, "depreciationAndAmortization")
    sga = canonical(df, "sellingGeneralAndAdministrativeExpenses")
    total_debt = canonical(df, "totalDebt")
    net_income = canonical(df, "netIncome")

    # Derived columns from earlier modules.
    roa = canonical(df, "roa")
    debt_to_assets = canonical(df, "debtToAssets")
    current_ratio = canonical(df, "currentRatio")
    gross_margin = canonical(df, "grossMargin")
    asset_turnover = canonical(df, "assetTurnover")
    cfo_to_net_income = canonical(df, "cfoToNetIncome")
    nwc = canonical(df, "nwc")

    new = {}

    # ---- Piotroski F-Score ----
    # Each signal is a boolean; an undeterminable signal (NaN input) evaluates to
    # False and therefore scores 0, matching the conventional treatment of missing
    # data in the F-Score.
    f_roa = roa > 0
    f_delta_roa = roa > lag(df, roa, 4)
    f_cfo = operating_cf > 0
    f_accruals = cfo_to_net_income > 1
    f_delta_leverage = debt_to_assets < lag(df, debt_to_assets, 4)
    f_delta_liquidity = current_ratio > lag(df, current_ratio, 4)
    f_no_dilution = shares_dil <= lag(df, shares_dil, 4)
    f_delta_gross_margin = gross_margin > lag(df, gross_margin, 4)
    f_delta_asset_turnover = asset_turnover > lag(df, asset_turnover, 4)

    new["fRoa"] = f_roa
    new["fDeltaRoa"] = f_delta_roa
    new["fCfo"] = f_cfo
    new["fAccruals"] = f_accruals
    new["fDeltaLeverage"] = f_delta_leverage
    new["fDeltaLiquidity"] = f_delta_liquidity
    new["fNoDilution"] = f_no_dilution
    new["fDeltaGrossMargin"] = f_delta_gross_margin
    new["fDeltaAssetTurnover"] = f_delta_asset_turnover
    new["fScoreTotal"] = (
        f_roa.astype(int)
        + f_delta_roa.astype(int)
        + f_cfo.astype(int)
        + f_accruals.astype(int)
        + f_delta_leverage.astype(int)
        + f_delta_liquidity.astype(int)
        + f_no_dilution.astype(int)
        + f_delta_gross_margin.astype(int)
        + f_delta_asset_turnover.astype(int)
    )

    # ---- Altman Z'' (non-manufacturing / emerging markets) ----
    z_wc_ta = safe_div(tca - tcl, total_assets)
    z_re_ta = safe_div(retained_earnings, total_assets)
    z_ebit_ta = safe_div(ebit, total_assets)
    z_bve_bvl = safe_div(equity, total_liabilities)
    new["zWcTa"] = z_wc_ta
    new["zReTa"] = z_re_ta
    new["zEbitTa"] = z_ebit_ta
    new["zBveBvl"] = z_bve_bvl
    new["altmanZScore"] = 6.56 * z_wc_ta + 3.26 * z_re_ta + 6.72 * z_ebit_ta + 1.05 * z_bve_bvl

    # ---- Beneish M-Score (year-ago comparisons) ----
    revenue_q4 = lag(df, revenue, 4)
    gross_profit_q4 = lag(df, gross_profit, 4)
    total_assets_q4 = lag(df, total_assets, 4)
    ppe_q4 = lag(df, ppe, 4)
    da_q4 = lag(df, da, 4)
    tcl_q4 = lag(df, tcl, 4)
    total_debt_q4 = lag(df, total_debt, 4)

    dsri = safe_div(
        safe_div(net_receivables, revenue),
        safe_div(lag(df, net_receivables, 4), revenue_q4),
    )
    gmi = safe_div(
        safe_div(revenue_q4 - gross_profit_q4, revenue_q4),
        safe_div(revenue - gross_profit, revenue),
    )
    aqi = safe_div(
        1 - safe_div(tca + ppe, total_assets),
        1 - safe_div(lag(df, tca, 4) + ppe_q4, total_assets_q4),
    )
    sgi = safe_div(revenue, revenue_q4)
    depi = safe_div(
        safe_div(da_q4, ppe_q4 + da_q4),
        safe_div(da, ppe + da),
    )
    sgai = safe_div(
        safe_div(sga, revenue),
        safe_div(lag(df, sga, 4), revenue_q4),
    )
    lvgi = safe_div(
        safe_div(total_debt + tcl, total_assets),
        safe_div(total_debt_q4 + tcl_q4, total_assets_q4),
    )
    tata = safe_div(net_income - operating_cf, total_assets)

    new["beneishDsri"] = dsri
    new["beneishGmi"] = gmi
    new["beneishAqi"] = aqi
    new["beneishSgi"] = sgi
    new["beneishDepi"] = depi
    new["beneishSgai"] = sgai
    new["beneishLvgi"] = lvgi
    new["beneishTata"] = tata
    new["mScoreTotal"] = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    # ---- Greenblatt Magic Formula (FS component) ----
    # Tangible operating capital; undefined when non-positive.
    greenblatt_capital = nwc + ppe
    new["greenblattRoic"] = safe_div(ebit, greenblatt_capital.where(greenblatt_capital > 0))

    return append(df, new)
