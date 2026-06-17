"""
Defines directory structure and path-building utilities for QuantBase data storage.
Handles creation of raw, clean, and market folders and provides helper functions
to build consistent file paths.
"""

import os
from glob import glob


# --------------- File names -------------
tickers_with_financials = "tickers.json"
ticker_profiles = "ticker_profiles.parquet"
classification_map = "classification_map.json"
market_errors = "market_errors.csv"
fundamental_errors = "fundamental_errors.csv"



# ---------------- Base paths ------------
WKD = os.path.dirname(os.path.abspath(__file__))
DATA_BASE = os.path.join(WKD, "..", "data")

RAW_BASE = os.path.join(DATA_BASE, "raw")
CLEAN_BASE = os.path.join(DATA_BASE, "clean")
MARKET_BASE = os.path.join(DATA_BASE, "market")
FUNDAMENTALS_BASE = os.path.join(DATA_BASE, "fundamentals")
ERROR_BASE = os.path.join(DATA_BASE, "errors")

# --------------- --------------
os.makedirs(RAW_BASE, exist_ok=True)
os.makedirs(CLEAN_BASE, exist_ok=True)
os.makedirs(MARKET_BASE, exist_ok=True)
os.makedirs(FUNDAMENTALS_BASE, exist_ok=True)
os.makedirs(ERROR_BASE, exist_ok=True)


# -------------- Build functions ---------------------
def build_clean(filename: str) -> str:
    """Return the path for a file in the clean data directory."""
    return os.path.join(CLEAN_BASE, filename)
def build_raw(filename: str) -> str:
    """Return the path for a file in the raw data directory."""
    return os.path.join(RAW_BASE, filename)
def build_market(filename: str) -> str:
    """Return the path for a file in the market data directory."""
    return os.path.join(MARKET_BASE, filename)
def build_fundamental(filename: str) -> str:
    """Return the path for a file in the fundamentals data directory."""
    return os.path.join(FUNDAMENTALS_BASE, filename)
def build_error(filename: str) -> str:
    """Return the path for a file in the error data directory."""
    return os.path.join(ERROR_BASE, filename)


# --------------- Special functions --------------------
def individual_profiles(ind: str) -> str:
    """Return the raw profile parquet path for an individual industry suffix."""
    filename = f"{ticker_profiles}_{ind}.parquet"
    return build_raw(filename)

def select_all(directory: str, filename: str = "", extension: str = ".parquet", und: str = "") -> list[str]:
    """
    Return a sorted list of files in directory matching filename_*extension,
    filename*extension, or filenameextension. If filename is empty, include all files.
    Extension must include the dot (e.g., '.parquet').
    """
    path = os.path.join(directory, f"{filename}{und}*{extension}")
    return sorted(glob(path))

def market_path_ind(symbol: str) -> str:
    """Return the per-symbol market parquet path."""
    return os.path.join(MARKET_BASE, f"{symbol}.parquet")
def fundamentals_path_ind(symbol: str) -> str:
    """Return the per-symbol fundamentals parquet path."""
    return os.path.join(FUNDAMENTALS_BASE, f"{symbol}.parquet")

# -----------------Reusable paths -------------------------
TICKERS_WITH_FINANCIALS_RAW = build_raw(tickers_with_financials)
TICKERS_WITH_FINANCIALS_CLEAN = build_clean(tickers_with_financials)
PROFILE_RAW = build_raw(ticker_profiles)
PROFILE_CLEAN = build_clean(ticker_profiles)
CLASSIFICATION_MAP_RAW = build_raw(classification_map)
CLASSIFICATION_MAP_CLEAN = build_clean(classification_map)
MARKET_ERRORS = build_error(market_errors)
FUNDAMENTAL_ERRORS = build_error(fundamental_errors)
