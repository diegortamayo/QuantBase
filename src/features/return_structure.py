"""
Compute multi-horizon return structure features for price data.

Includes cumulative returns, log returns, drawdowns, distance to highs/lows,
and basic distribution metrics over defined rolling periods.
"""

from config.features_config import *

import pandas as pd
import numpy as np


def return_structure_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate rolling return and risk metrics across multiple horizons.

    Args:
        df: DataFrame with at least a 'close' price column.

    Returns:
        DataFrame with appended multi-period return, drawdown, and statistical features.
    """
    def max_draw(x):
        return np.min(x / np.maximum.accumulate(x) - 1)

    new_columns = {}

    df["ret_1d"] = df["close"].pct_change()
    df["log_r_1d"] = np.log(1 + df["ret_1d"])
    for period in MULTI_HORIZONS:
        new_columns[f"ret_{period}d"] = df["close"].pct_change(period)
        new_columns[f"cum_ret_{period}d"] = (1 + df[f"ret_1d"]).rolling(period).apply(np.prod, raw=True)
        new_columns[f"log_r_{period}d"] = df["log_r_1d"].rolling(period).sum()
        new_columns[f"distance_high_{period}d"] = df["close"]/df["close"].rolling(period).max() - 1
        new_columns[f"distance_low_{period}d"] = df["close"]/df["close"].rolling(period).min() - 1
        new_columns[f"max_dd_{period}d"] = df["close"].rolling(period, min_periods=1).apply(max_draw, raw=True)
        new_columns[f"hit_ratio_{period}d"] = df["ret_1d"].rolling(period, min_periods=1).apply(lambda x: (x>0).mean(), raw=True)
        if period != 5:
            new_columns[f"skew_{period}d"] = df["ret_1d"].rolling(period).skew()
            new_columns[f"kurt_{period}d"] = df["ret_1d"].rolling(period).kurt()
            new_columns[f"autocorr_{period}d"] = df["ret_1d"].rolling(period).apply(lambda x: x.autocorr(lag=1))

    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))

    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
