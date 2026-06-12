"""
Configurations and constants for features calculations
"""

from datetime import timedelta

MULTI_HORIZONS = [5, 21, 63, 126, 252, 504]
SHORT_HORIZONS = [5, 21]
MID_HORIZONS = [63, 126]
LONG_HORIZONS = [252, 504]

BATCH_SIZE = 50
N_WORKERS = 8
N_BATCH_COOLDOWN = 5
COOLDOWN_TIME = 10

VALID_FEATURE_TYPES = ["market", "fundamental"]


# --------------- Fundamental feature settings ---------------
# Days used to annualize a single quarter for the activity ratios (DSO/DIO/DPO).
DAYS_IN_QUARTER = 90

# Number of trailing quarters summed for a TTM (trailing-twelve-month) aggregate.
TTM_QUARTERS = 4

# Calendar tolerance for the fundamental->market price join. The spec asks for the
# next trading day within 5 *trading* days of the filing date; on a continuous daily
# series that is at most a long weekend plus holidays away, so ~7 calendar days is a
# faithful, vectorizable encoding of that window (and also rejects filings that fall
# after the end of the available price history).
PRICE_JOIN_TOLERANCE = timedelta(days=7)

# Base line items for which QoQ / YoY / TTM-CAGR growth rates are computed.
GROWTH_BASE_COLUMNS = [
    "revenue",
    "grossProfit",
    "ebit",
    "netIncome",
    "epsDiluted",
    "capitalExpenditure",
    "totalStockholdersEquity",
]

# CAGR variants: label -> (quarter lag, number of years).
CAGR_HORIZONS = {
    "cagr_3y": (12, 3),
    "cagr_5y": (20, 5),
}