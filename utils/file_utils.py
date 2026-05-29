
from config.data_paths import select_all, MARKET_BASE

import pandas as pd
import numpy as np


def test_len():
    all_files = select_all(MARKET_BASE)
    df_data = {"file": all_files, "size": []}
    for file in all_files:
        df = pd.read_parquet(file)
        df_data["size"].append(len(df))
    return pd.DataFrame(df_data)


def file_stats():
    df = test_len()
    df[">1000"] = df["size"] > 1000
    print(df[">1000"].sum())
    size_col = df["size"]

    print(size_col.skew())

    mean = size_col.mean()
    std = size_col.std()
    df["zscore"] = (size_col - mean)/std

    median = size_col.median()
    mad = np.median(np.abs(size_col - median))
    df["median_zscore"] = (size_col - median)/mad

    return df


# stats = file_stats()
# print(stats.to_string())
