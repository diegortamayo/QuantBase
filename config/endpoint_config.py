"""
Centralize Financial Modeling Prep API endpoints, request limits, and schemas.

Defines reusable endpoint names, rate-limit settings, response field lists, and
filter flags used by the data ingestion and normalization pipelines.
"""

from config.keys import FMP_KEY


# --------------- BASE API SETTINGS ---------------------
FMP_BASE_URL = "https://financialmodelingprep.com/stable/"
FMP_API_KEY = FMP_KEY

SETKEY = f"apikey={FMP_API_KEY}"

RATE_LIMIT = 290
LIMIT_SECONDS = 60


# --------------- ENDPOINTS ---------------------
AVAILABLE_SECTOR_ENDPOINT = "available-sectors"
AVAILABLE_INDUSTRY_ENDPOINT = "available-industries"
FIN_STATEMENT_SYMBOLS_ENDPOINT = "financial-statement-symbol-list"
ALL_SYMBOLS_ENDPOINT = "stock-list"
PROFILE_ENDPOINT = "profile"

FIVEMIN_MARKET_ENDPOINT = "historical-chart/5min"
DAILY_MARKET_ENDPOINT = "historical-price-eod/full"
START_DATE = "2017-01-01"

# Financial statements
INCOME_STATEMENT_ENDPOINT = "income-statement"
BALANCE_SHEET_ENDPOINT = "balance-sheet-statement"
CASH_FLOW_STATEMENT_ENDPOINT = "cash-flow-statement"



# FUNDAMENTAL ENDPOINT SETTINGS
YEARS_LIMIT = 8
QUARTER_LIMIT = YEARS_LIMIT*4


STYPES = ["income", "cash", "balance"]
STATEMENT_ENDPOINTS = {
    STYPES[0]: INCOME_STATEMENT_ENDPOINT,
    STYPES[1]: CASH_FLOW_STATEMENT_ENDPOINT,
    STYPES[2]: BALANCE_SHEET_ENDPOINT
}

REQ_PER_TICKER_FUNDAMENTALS = 3
HEADER_KEYS = ["date", "symbol", "reportedCurrency", "cik", "filingDate", "acceptedDate", "fiscalYear", "period"]

# Suffix appended to line items that appear on more than one statement, so each
# statement keeps its own value through the merge (the cash-flow copies are period
# deltas while balance-sheet copies are levels, so they genuinely differ).
STATEMENT_SUFFIXES = {
    STYPES[0]: "_is",
    STYPES[1]: "_cf",
    STYPES[2]: "_bs",
}



# --------------- FIELDS ---------------------
PROFILE_FIELDS = [
    "symbol","price","marketCap","beta","lastDividend","range","change","changePercentage","volume","averageVolume",
    "companyName","currency","cik","isin","cusip","exchangeFullName","exchange","industry","website","description",
    "ceo","sector","country","fullTimeEmployees","phone","address","city","state","zip","image","ipoDate",
    "defaultImage","isEtf","isActivelyTrading","isAdr","isFund","error"
]

CLEAN_PROFILE_FILEDS = ["symbol", "cik", "isin", "exchange", "sector", "industry", "country", "ipoDate", "marketCap", "price", "averageVolume", "companyName"]

OHLCV_FIELDS = ["symbol", "date", "open", "high", "low", "close", "volume", "changePercent", "vwap", "error"]


# --------------- MISCELANEOUS---------------------
ACTIVE_TRADING_FLAG = True
ADR_FLAG = False
ETF_FLAG = False
TRADED_EXCHANGES = [
    "NYSE",
    "NASDAQ",
]
INDUSTRY_EXLCUSIONS = ["Shell Companies"]
EXCLUSION_TERMS = ["preferred", "series", "warrant", "note", "bond", "debenture", "subordinated"]
