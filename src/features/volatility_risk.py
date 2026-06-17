"""
Compute volatility and risk-adjusted performance metrics.

Includes realized volatility, ATR, downside deviation, rolling Sharpe and Sortino ratios,
and volatility ratio features across multiple horizons.

Depends on return_structure features for 'ret_1d'.
"""

from config.features_config import *

import numpy as np
import pandas as pd

# This module is dependent on return structure for ret_1d

# Beta to index and idiosyncratic vol


def rolling_sharpe(mean, std):
    """Return the rolling Sharpe-like ratio from mean return and volatility."""
    return mean / std

def rolling_sortino(mean_ret, downside_dev):
    """Return the rolling Sortino-like ratio from mean return and downside deviation."""
    return mean_ret / downside_dev


def volatility_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate volatility and risk-return ratio features.

    Args:
        df: DataFrame containing 'close', 'high', 'low', and 'ret_1d' columns.

    Returns:
        DataFrame with realized volatility, ATR, Sharpe, Sortino, and volatility ratio features.
    """

    new_columns = {}
    tr = np.maximum(df["high"] - df["low"], np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1))))
    neg = df["ret_1d"].clip(upper=0)
    for period in MULTI_HORIZONS:
        roll_1d = df["ret_1d"].rolling(period, min_periods=5)
        roll_1d_mean = roll_1d.mean()
        roll_1d_std = roll_1d.std()
        new_columns[f"realized_vol_{period}d"] = roll_1d_std

        if period in SHORT_HORIZONS or period in MID_HORIZONS:
            new_columns[f"atr_{period}d"] = tr.rolling(period, min_periods=1).mean() / df["close"]

        if period in MID_HORIZONS or period in LONG_HORIZONS:
            new_columns[f"downside_dev_{period}d"] = neg.rolling(period, min_periods=5).std()
            new_columns[f"rolling_sharpe_{period}d"] = rolling_sharpe(roll_1d_mean, roll_1d_std)
            new_columns[f"rolling_sortino_{period}d"] = rolling_sortino(roll_1d_mean, new_columns[f"downside_dev_{period}d"])

    new_columns["vol_ratio_5_21"] = new_columns["realized_vol_5d"] / new_columns["realized_vol_21d"]
    new_columns["vol_ratio_21_63"] = new_columns["realized_vol_21d"] / new_columns["realized_vol_63d"]
    new_columns["vol_ratio_63_126"] = new_columns["realized_vol_63d"] / new_columns["realized_vol_126d"]

    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))

    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
