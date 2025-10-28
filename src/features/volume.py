"""
Compute volume-based liquidity and volatility features.

Includes average dollar volume, rolling log-volume volatility,
and volume z-scores across multiple horizons.
"""

from config.features_config import MULTI_HORIZONS

import pandas as pd
import numpy as np


def volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate rolling volume and liquidity metrics.

    Args:
        df: DataFrame containing 'close' and 'volume' columns.

    Returns:
        DataFrame with average dollar volume, volume volatility, and z-score features.
    """
    new_columns = {}

    df["log_volume"] = np.log(df["volume"])
    for period in MULTI_HORIZONS:
        new_columns[f"avg_dol_volume_{period}d"] = (df["volume"] * df["close"]).rolling(period).mean()
        new_columns[f"volume_vol_{period}d"] = df["log_volume"].rolling(period, min_periods=1).std()
        roll = df["volume"].rolling(period)
        new_columns[f"volume_zscore_{period}d"] = (df["volume"] - roll.mean()) / roll.std()

    drop_cols = set(new_columns) & set(df.columns)
    if drop_cols:
        df = df.drop(columns=list(drop_cols))
    return pd.concat([df, pd.DataFrame(new_columns, index=df.index)], axis=1)
