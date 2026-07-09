"""
Compute multi-horizon return structure features for price data.

Includes cumulative returns, log returns, drawdowns, distance to highs/lows,
and basic distribution metrics over defined rolling periods.
"""

from config.features_config import *

import pandas as pd
import numpy as np


def _max_draw(x: np.ndarray) -> float:
    """Return maximum drawdown within a rolling price window."""
    return np.min(x/np.maximum.accumulate(x) - 1.0)

def _autocorr_lag1(x: np.ndarray) -> float:
    x0 = x[:-1]
    x1 = x[1:]

    mask = np.isfinite(x0) & np.isfinite(x1)
    x0 = x0[mask]
    x1 = x1[mask]

    if len(x0) < 2:
        return np.nan

    x0 = x0 - x0.mean()
    x1 = x1 - x1.mean()

    denom = np.sqrt(np.sum(x0 ** 2) * np.sum(x1 ** 2))
    if denom == 0:
        return np.nan

    return np.sum(x0 * x1) / denom



def return_structure_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate rolling return and risk metrics across multiple horizons.

    Args:
        df: DataFrame with at least a 'close' price column.

    Returns:
        DataFrame with appended multi-period return, drawdown, and statistical features.
    """
    
    close = df["close"]
    ret_1d = close.pct_change()
    log_r_1d = np.log(1 + ret_1d)
    positive_ret = ret_1d.gt(0).astype(float)

    new_columns = {
        "ret_1d": ret_1d,
        "log_r_1d": log_r_1d
    }

    for period in MULTI_HORIZONS:
        rolling_close = close.rolling(period)
        rolling_ret = ret_1d.rolling(period)

        new_columns[f"log_r_{period}d"] = log_r_1d.rolling(period).sum()
        new_columns[f"distance_high_{period}d"] = close/rolling_close.max() - 1
        new_columns[f"distance_low_{period}d"] = close/rolling_close.min() - 1

        if period >= SHORT_HORIZONS[-1]:
            new_columns[f"max_dd_{period}d"] = rolling_close.apply(_max_draw, raw=True)
            new_columns[f"hit_ratio_{period}d"] = positive_ret.rolling(period).mean()
            new_columns[f"autocorr_{period}d"] = ret_1d.rolling(period - 1, min_periods=period - 1).corr(
                ret_1d.shift(1))
        if period not in SHORT_HORIZONS:
            new_columns[f"skew_{period}d"] = ret_1d.rolling(period).skew()
            new_columns[f"kurt_{period}d"] = ret_1d.rolling(period).kurt()

    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))

    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
