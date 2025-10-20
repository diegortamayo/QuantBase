import os
from glob import glob
from operator import index

# --------------- File names -------------
tickers_with_financials = "tickers.json"
ticker_profiles = "ticker_profiles.parquet"
classification_map = "classification_map.json"



# ---------------- Base paths ------------
WKD = os.path.dirname(os.path.abspath(__file__))
DATA_BASE = os.path.join(WKD, "..", "data")

RAW_BASE = os.path.join(DATA_BASE, "raw")
CLEAN_BASE = os.path.join(DATA_BASE, "clean")
MARKET_BASE = os.path.join(DATA_BASE, "market")


# --------------- --------------
os.makedirs(RAW_BASE, exist_ok=True)
os.makedirs(CLEAN_BASE, exist_ok=True)
os.makedirs(MARKET_BASE, exist_ok=True)


# -------------- Build functions ---------------------
def build_clean(filename: str) -> str:
    return os.path.join(CLEAN_BASE, filename)
def build_raw(filename: str) -> str:
    return os.path.join(RAW_BASE, filename)
def build_market(filename: str) -> str:
    return os.path.join(MARKET_BASE, filename)


# --------------- Special functions --------------------
def individual_profiles(ind: str) -> str:
    filename = f"{ticker_profiles}_{ind}.parquet"
    return build_raw(filename)

def select_all(directory, filename, extension, und = "_") -> list[str]:
    path = os.path.join(directory, f"{filename}{und}*{extension}")
    return sorted(glob(path))

def market_path_ind(symbol: str) -> str:
    return os.path.join(MARKET_BASE, f"{symbol}.parquet")

# -----------------Reusable paths -------------------------
TICKERS_WITH_FINANCIALS_RAW = build_raw(tickers_with_financials)
TICKERS_WITH_FINANCIALS_CLEAN = build_clean(tickers_with_financials)
PROFILE_RAW = build_raw(ticker_profiles)
PROFILE_CLEAN = build_clean(ticker_profiles)
CLASSIFICATION_MAP_RAW = build_raw(classification_map)
CLASSIFICATION_MAP_CLEAN = build_clean(classification_map)

