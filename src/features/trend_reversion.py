from config.features_config import *

import pandas as pd
import numpy as np

def trend_reversion_features(df: pd.DataFrame):
    def deviation_percentile(close, per):
        roll = close.rolling(per, min_periods=5)
        roll_min = roll.min()
        roll_max = roll.max()
        return (close - roll_min) / (roll_max - roll_min)

    new_columns = {}
    log_close = np.log(df["close"])

    new_columns["12-1_momentum"] = df["close"].shift(21) / df["close"].shift(252) - 1
    new_columns["r_negative"] = -df["ret_1d"].shift(1)

    for period in MULTI_HORIZONS:
        ema = df["close"].ewm(span=period, adjust=False, min_periods=5).mean()
        new_columns[f"ema_distance_{period}d"] = df["close"]/ema - 1
        new_columns[f"deviation_percentile_{period}d"] = deviation_percentile(df["close"], period)

        if period in SHORT_HORIZONS or period in MID_HORIZONS:
            mu = log_close.rolling(period, min_periods=5).mean()
            sigma = log_close.rolling(period, min_periods=5).std()
            new_columns[f"reversion_zscore_{period}d"] = (log_close - mu) /sigma

        x = np.arange(period)
        x_mean = x.mean()
        denom = sum((x - x_mean) ** 2)

        def slope_tstat(y):
            if len(y) < period:
                return np.nan
            y_mean = y.mean()
            cov_xy = np.sum((x - x_mean) * (y - y_mean))
            beta = cov_xy / denom
            y_hat = y_mean + beta * (x - x_mean)
            residual = y - y_hat
            std_error = np.sqrt(np.sum(residual ** 2) / (period - 2))
            std_error_beta = std_error / np.sqrt(denom)
            return beta / std_error_beta if std_error_beta != 0 else np.nan

        new_columns[f"zscore_regression_{period}d"] = log_close.rolling(period).apply(slope_tstat, raw=False)

        if period != SHORT_HORIZONS[0]:
            new_columns[f"log_close_slope{period}d"] = log_close.rolling(period).apply(
                lambda y: np.cov(x, y)[0, 1] / denom if len(y) == period else np.nan, raw=False
            )

    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))

    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
