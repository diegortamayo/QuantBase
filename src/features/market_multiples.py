"""
Compute market-dependent fundamental features by joining each quarterly filing to a
price.

Each fundamental record is matched to the first tradable price after the filing is
available. Post-market filings use the next trading day's open; other filings use the
close on or after the filing date. A forward as-of join with a PRICE_JOIN_TOLERANCE
window prevents look-ahead bias and yields NaN (so every market-dependent feature for
that record is NaN) when no price is found in time. From the matched price it builds
market cap and enterprise value, the valuation multiples (TTM denominators for flow
variables), the size/value factor inputs and the Greenblatt earnings yield.

Reads (semantic line items): weightedAverageShsOutDil, totalDebt,
    cashAndShortTermInvestments, minorityInterest, totalStockholdersEquity, revenue,
    epsDiluted, freeCashFlow, ebit, ebitda, operatingCashFlow, totalAssets; and derived
    columns invested_capital, revenue_yoy. Reads from market_df: date, close.

Produces: price_at_filing, market_cap, ev, book_value_per_share, pe, pb, ps, p_fcf,
    ev_ebit, ev_ebitda, ev_sales, ev_fcf, earnings_yield, fcf_yield, peg, ev_ic,
    log_market_cap, log_total_assets, book_to_market, earnings_to_price, cfo_to_price,
    sales_to_price, greenblatt_earnings_yield.
"""

import numpy as np
import pandas as pd
from datetime import time

from config.features_config import PRICE_JOIN_TOLERANCE

from ._fundamentals_helpers import canonical, append, safe_div, safe_div_pos, ttm


MARKET_CLOSE_TIME = time(16, 0)


def _filing_price_reference(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Build the first date/price-type pair usable after the filing was available.

    acceptedDate usually contains the filing timestamp. If the filing was accepted
    after the market close, the first tradable regular-session price is the next
    session's open. Other filings use the close on or after the filing date.
    filingDate has no time, so the fallback starts on the next calendar day and
    uses the close.
    """
    accepted_raw = df["acceptedDate"] if "acceptedDate" in df.columns else pd.Series(pd.NaT, index=df.index)
    filing_raw = df["filingDate"] if "filingDate" in df.columns else pd.Series(pd.NaT, index=df.index)

    accepted = pd.to_datetime(accepted_raw, errors="coerce")
    filing = pd.to_datetime(filing_raw, errors="coerce")

    ref = accepted.dt.normalize()
    after_close = accepted.notna() & (accepted.dt.time >= MARKET_CLOSE_TIME)
    ref = ref.where(~after_close, ref + pd.Timedelta(days=1))

    filing_ref = filing.dt.normalize() + pd.Timedelta(days=1)
    return ref.fillna(filing_ref), after_close


def _attach_filing_price(df: pd.DataFrame, market_df: pd.DataFrame) -> pd.Series:  # * *? ---------------------------
    """
    Match each filing to the first tradable price after its reference timestamp.

    Args:
        df: Fundamental DataFrame (uses acceptedDate, falling back to filingDate).
        market_df: Market DataFrame with 'date', 'open', and 'close', or None.

    Returns:
        Series of matched prices aligned to df.index; NaN where no price is
        available within PRICE_JOIN_TOLERANCE. Post-market filings use the next
        trading day's open; other filings use a close.
    """
    close = pd.Series(np.nan, index=df.index, dtype="float64")
    if market_df is None or "close" not in market_df.columns or "open" not in market_df.columns or market_df.empty:
        return close

    ref, use_next_open = _filing_price_reference(df)

    md_cols = ["date", "close", "open"]
    md = market_df[md_cols].copy()
    md["date"] = pd.to_datetime(md["date"], errors="coerce")
    md["close"] = pd.to_numeric(md["close"], errors="coerce")
    md["open"] = pd.to_numeric(md["open"], errors="coerce")
    md = md.dropna(subset=["date", "close", "open"]).sort_values("date")
    if md.empty:
        return close

    left = ref.dropna().sort_values()
    if left.empty:
        return close

    matched = pd.merge_asof(
        pd.DataFrame({"ref": left.values}, index=left.index),
        md,
        left_on="ref",
        right_on="date",
        direction="forward",
        tolerance=PRICE_JOIN_TOLERANCE,
    )
    price = matched["close"].copy()
    open_mask = use_next_open.reindex(left.index).fillna(False).to_numpy()
    price.loc[open_mask] = matched.loc[open_mask, "open"]
    close.loc[left.index] = price.values
    return close


def fundamental_market_features(df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate market-dependent valuation and factor features.

    Args:
        df: Per-ticker fundamental DataFrame with FS features already computed
            (needs 'invested_capital' and 'revenue_yoy').
        market_df: Matching per-ticker market DataFrame, or None if unavailable.

    Returns:
        DataFrame with market-dependent features appended (all NaN when no price
        could be joined).
    """
    close = _attach_filing_price(df, market_df)

    shares_dil = canonical(df, "weightedAverageShsOutDil")
    total_debt = canonical(df, "totalDebt")
    cash_sti = canonical(df, "cashAndShortTermInvestments")
    minority_interest = canonical(df, "minorityInterest")
    equity = canonical(df, "totalStockholdersEquity")
    revenue = canonical(df, "revenue")
    eps_diluted = canonical(df, "epsDiluted")
    fcf = canonical(df, "freeCashFlow")
    ebit = canonical(df, "ebit")
    ebitda = canonical(df, "ebitda")
    operating_cf = canonical(df, "operatingCashFlow")
    total_assets = canonical(df, "totalAssets")
    invested_capital = canonical(df, "invested_capital")
    revenue_yoy = canonical(df, "revenue_yoy")

    # TTM denominators for flow variables.
    eps_ttm = ttm(df, eps_diluted)
    revenue_ttm = ttm(df, revenue)
    fcf_ttm = ttm(df, fcf)
    ebit_ttm = ttm(df, ebit)
    ebitda_ttm = ttm(df, ebitda)
    cfo_ttm = ttm(df, operating_cf)

    market_cap = close * shares_dil
    ev = market_cap + total_debt - cash_sti + minority_interest

    new = {}
    new["priceAtFiling"] = close
    new["marketCap"] = market_cap
    new["ev"] = ev
    new["bookValuePerShare"] = safe_div(equity, shares_dil)

    # Valuation multiples.
    new["pe"] = safe_div_pos(close, eps_ttm)
    new["pb"] = safe_div(market_cap, equity)
    new["ps"] = safe_div(market_cap, revenue_ttm)
    new["pfcf"] = safe_div_pos(market_cap, fcf_ttm)
    new["evEbit"] = safe_div_pos(ev, ebit_ttm)
    new["evEbitda"] = safe_div_pos(ev, ebitda_ttm)
    new["evSales"] = safe_div(ev, revenue_ttm)
    new["evFcf"] = safe_div_pos(ev, fcf_ttm)
    new["earningsYield"] = safe_div(eps_ttm, close)
    new["fcfYield"] = safe_div(fcf_ttm, market_cap)
    # Growth proxy is revenue YoY; PEG is undefined for non-positive growth.
    new["peRevGrowth"] = safe_div_pos(new["pe"], revenue_yoy)
    new["evic"] = safe_div(ev, invested_capital)

    # Size / value factor inputs.
    new["logMarketCap"] = np.log(market_cap.where(market_cap > 0))
    new["logTotalAssets"] = np.log(total_assets.where(total_assets > 0))
    new["bookToMarket"] = safe_div(equity, market_cap)
    new["earningsToPrice"] = safe_div(eps_ttm, close)
    new["cfoToPrice"] = safe_div(cfo_ttm, market_cap)
    new["salesToPrice"] = safe_div(revenue_ttm, market_cap)

    # Greenblatt earnings yield (market component).
    new["greenblattEarningsYield"] = safe_div_pos(ebit_ttm, ev)

    return append(df, new)
