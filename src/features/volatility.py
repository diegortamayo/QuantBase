from config.features_config import *

import numpy as np

# This module is dependent on return structure for ret_1d

# Beta to index and idiosyncratic vol


def rolling_sharpe(mean, std):
    return mean / std

def rolling_sortino(mean_ret, downside_dev):
    return mean_ret / downside_dev


def volatility_risk_features(df):
    tr = np.maximum(df["high"] - df["low"], np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1))))
    neg = df["ret_1d"].clip(upper=0)
    for period in MULTI_HORIZONS:
        roll_1d = df["ret_1d"].rolling(period, min_periods=5)
        roll_1d_mean = roll_1d.mean()
        roll_1d_std = roll_1d.std()
        df[f"realized_vol_{period}d"] = roll_1d_std

        if period in SHORT_HORIZONS or period in MID_HORIZONS:
            df[f"atr_{period}d"] = tr.rolling(period, min_periods=1).mean() / df["close"]

        if period in MID_HORIZONS or period in LONG_HORIZONS:
            df[f"downside_dev_{period}d"] = neg.rolling(period, min_periods=5).std()
            df[f"rolling_sharpe_{period}d"] = rolling_sharpe(roll_1d_mean, roll_1d_std)
            df[f"rolling_sortino_{period}d"] = rolling_sortino(roll_1d_mean, df[f"downside_dev_{period}d"])

    df["vol_ratio_5_21"] = df["realized_vol_5d"] / df["realized_vol_21d"]
    df["vol_ratio_21_63"] = df["realized_vol_21d"] / df["realized_vol_63d"]
    df["vol_ratio_63_126"] = df["realized_vol_63d"] / df["realized_vol_126d"]
