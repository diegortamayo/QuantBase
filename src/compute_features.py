"""
Compute all engineered features for every market file in parallel.

Applies return structure, volume, trend-reversion, and volatility features
to all parquet files in MARKET_BASE using batched multiprocessing.
"""

from config.data_paths import MARKET_BASE
from config.features_config import BATCH_SIZE, N_WORKERS, N_BATCH_COOLDOWN, COOLDOWN_TIME
from features import *

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import time, gc

import pandas as pd


FEATURE_FUNCTIONS = [
    return_structure_features,
    volume_features,
    trend_reversion_features,
    volatility_risk_features,
]


def process_file(file_path: str) -> str:
    """
    Apply all feature functions to a single parquet file.

    Args:
        file_path: Path to input parquet file.

    Returns:
        Stem name of the processed file.
    """

    df = pd.read_parquet(file_path)
    df = df.sort_values("date").reset_index(drop=True)

    for func in FEATURE_FUNCTIONS:
        df = func(df)

    df.to_parquet(file_path)
    return Path(file_path).stem


def compute_features_all() -> None:
    """
    Run batched multiprocessing to compute features for all market files.

    Uses N_WORKERS parallel processes, batch size BATCH_SIZE, and cooldown
    after every N_BATCH_COOLDOWN batches to manage memory load.
    """

    files = [f for f in Path(MARKET_BASE).glob("*.parquet")]
    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        for i in range(0, len(files), BATCH_SIZE):
            batch = files[i:i+BATCH_SIZE]
            futures = [executor.submit(process_file, f) for f in batch]
            for fut in as_completed(futures):
                print(f"Finished features for: {fut.result()}")
            print(f"Finished batch number {i}-{i+BATCH_SIZE}")

            if (i // BATCH_SIZE+1) % N_BATCH_COOLDOWN == 0:
                gc.collect()
                time.sleep(COOLDOWN_TIME)


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    compute_features_all()
