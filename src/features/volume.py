from config.features_config import MULTI_HORIZONS

import pandas as pd
import numpy as np


def volume_features(df: pd.DataFrame) -> pd.DataFrame:
    df["log_volume"] = np.log(df["volume"])
    for period in MULTI_HORIZONS:
        df[f"avg_dol_volume_{period}d"] = (df["volume"] * df["close"]).rolling(period).mean()
        df[f"volume_vol_{period}d"] = df["log_volume"].rolling(period, min_periods=1).std()
        roll = df["volume"].rolling(period)
        df[f"volume_zscore_{period}d"] = (df["volume"] - roll.mean()) / roll.std()

    return df
