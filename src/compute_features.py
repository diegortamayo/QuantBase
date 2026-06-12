"""
Compute all engineered features for every market and fundamental file in parallel.

For market files: applies return structure, volume, trend-reversion, and volatility
features to all parquet files in MARKET_BASE.

For fundamental files: applies the financial-statement feature chain (profitability,
leverage/liquidity, cash-flow/accruals, valuation inputs, growth, composite scores)
followed by the market-dependent valuation/factor features, joining each filing to its
matching market file in MARKET_BASE.

Both pipelines use batched multiprocessing.
"""

from config.data_paths import MARKET_BASE, FUNDAMENTALS_BASE, market_path_ind
from config.features_config import BATCH_SIZE, N_WORKERS, N_BATCH_COOLDOWN, COOLDOWN_TIME, VALID_FEATURE_TYPES
from features import *

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import os, time, gc

import pandas as pd


FEATURE_FUNCTIONS = [
    return_structure_features,
    volume_features,
    trend_reversion_features,
    volatility_risk_features,
]

# Financial-statement feature chain. Order matters: later functions read columns
# produced by earlier ones (e.g. valuation inputs use 'nopat'/'roe' from
# profitability, and the scores use roa/current_ratio/nwc from earlier modules).
FUNDAMENTAL_FEATURE_FUNCTIONS = [
    profitability_features,
    leverage_liquidity_features,
    cashflow_accruals_features,
    valuation_input_features,
    growth_features,
    score_features,
]


def process_market_file(file_path: str) -> str:
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


def process_fundamental_file(file_path: str) -> str:
    """
    Apply the full fundamental feature pipeline to a single ticker's parquet file.

    Runs the financial-statement feature chain in dependency order, then joins the
    matching market file to compute the market-dependent valuation/factor features.
    Features are written back in place, matching the market pipeline convention.

    Args:
        file_path: Path to a per-ticker fundamental parquet file.

    Returns:
        Stem name (ticker symbol) of the processed file.
    """

    df = pd.read_parquet(file_path)
    df = df.sort_values("date").reset_index(drop=True)

    for func in FUNDAMENTAL_FEATURE_FUNCTIONS:
        df = func(df)

    symbol = Path(file_path).stem
    market_path = market_path_ind(symbol)
    market_df = pd.read_parquet(market_path) if os.path.exists(market_path) else None
    df = fundamental_market_features(df, market_df)

    df.to_parquet(file_path)
    return symbol


def compute_features_all(feature_type: str):
    if feature_type not in VALID_FEATURE_TYPES:
        raise ValueError(f"Invalid argument, feature_type must exist in ['fundamental', 'market']")

    if feature_type == VALID_FEATURE_TYPES[1]:
        func = process_fundamental_file
        # files = [f for f in Path(FUNDAMENTALS_BASE).glob("*.parquet")]
        files = [
            Path(FUNDAMENTALS_BASE) / "AAPL.parquet",
            Path(FUNDAMENTALS_BASE) / "MRNA.parquet",
            Path(FUNDAMENTALS_BASE) / "PYPL.parquet",
        ]
    else:
        func = process_market_file
        files = [f for f in Path(MARKET_BASE).glob("*.parquet")]

    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        for i in range(0, len(files), BATCH_SIZE):
            batch = files[i:i+BATCH_SIZE]
            futures = [executor.submit(func, f) for f in batch]
            for fut in as_completed(futures):
                print(f"Finished features for: {fut.result()}")
            print(f"Finished batch number {i}-{i+len(batch)}")

            if (i // BATCH_SIZE+1) % N_BATCH_COOLDOWN == 0:
                gc.collect()
                time.sleep(COOLDOWN_TIME)


if __name__ == "__main__":
    compute_features_all("fundamental")
