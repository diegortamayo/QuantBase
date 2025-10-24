from config.data_paths import MARKET_BASE
from config.features_config import BATCH_SIZE, N_WORKERS
from features import *

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd


FEATURE_FUNCTIONS = [
    return_structure_features,
    volume_features,
    trend_reversion_features,
    volatility_risk_features,
]


def process_file(file_path: str):
    df = pd.read_parquet(file_path)

    for func in FEATURE_FUNCTIONS:
        df = func(df)

    df.to_parquet(file_path)
    return Path(file_path).stem


def compute_features_all():
    files = [f for f in Path(MARKET_BASE).glob("*.parquet")]
    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        for i in range(0, len(files), BATCH_SIZE):
            batch = files[i:i+BATCH_SIZE]
            futures = [executor.submit(process_file, f) for f in batch]
            for fut in as_completed(futures):
                print(f"Finished features for: {fut.result()}")

