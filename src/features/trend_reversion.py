"""
Compute trend and reversion-based technical features for price data.

Includes exponential moving average distance, deviation percentiles,
z-score mean reversion, regression slope t-stats, and log-return slopes
across multiple horizons.

Depends on return_structure code running first
"""

from config.features_config import *

import pandas as pd
import numpy as np


def _deviation_percentile(close, p):
    """Return each price's percentile position within its rolling high-low range."""
    roll = close.rolling(p, min_periods=5)
    roll_min = roll.min()
    roll_max = roll.max()
    # NaN instead of +/-inf when the window is perfectly flat (max == min).
    price_range = roll_max - roll_min
    return (close - roll_min) / price_range.where(price_range > 0)


def _rolling_ols(log_close: pd.Series, p: int) -> tuple[pd.Series, pd.Series]:
    """Vectorized rolling OLS of log-price on time: (slope t-stat, slope)."""
    y = log_close.to_numpy(dtype="float64")
    yc = y - np.nanmean(y)  # conditioning only; beta is shift invariant
    x_mean = (p - 1) / 2.0
    denom = p * (p * p - 1) / 12.0
    w = np.arange(p) - x_mean
    beta = np.convolve(yc, w[::-1], mode="valid") / denom
    syy = (log_close.rolling(p).var(ddof=1) * (p-1)).to_numpy()[p-1:]
    rss = np.maximum(syy - beta * beta * denom, 0.0)
    se_beta = np.sqrt(rss / (p-2) / denom)
    tstat = np.divide(beta, se_beta, out=np.full_like(beta, np.nan), where=se_beta>0)
    pad = np.full(p-1, np.nan)
    return (pd.Series(np.concatenate([pad, tstat]), index=log_close.index),
            pd.Series(np.concatenate([pad, beta]), index=log_close.index))


def trend_reversion_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate trend and reversion metrics across multi-horizon windows.

    Args:
        df: DataFrame with 'close' and 'ret_1d' columns.

    Returns:
        DataFrame with added trend strength, reversion, and momentum features.
    """

    new_columns = {}
    log_close = np.log(df["close"])

    new_columns["12-1_momentum"] = df["close"].shift(21) / df["close"].shift(252) - 1
    new_columns["r_negative"] = -df["ret_1d"].shift(1)

    for period in MULTI_HORIZONS:
        ema = df["close"].ewm(span=period, adjust=False, min_periods=5).mean()
        new_columns[f"ema_distance_{period}d"] = df["close"]/ema - 1
        new_columns[f"deviation_percentile_{period}d"] = _deviation_percentile(df["close"], period)

        mu = log_close.rolling(period, min_periods=5).mean()
        sigma = log_close.rolling(period, min_periods=5).std()
        new_columns[f"reversion_zscore_{period}d"] = (log_close - mu) /sigma

        new_columns[f"zscore_regression_{period}d"], new_columns[f"log_close_slope{period}d"] = _rolling_ols(log_close, period)

    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))

    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
